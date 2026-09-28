"""
Import Plex video playlists from JSON files exported by export_playlists.py.

Requires: pip install plexapi
"""

import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field

from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin

SUPPORTED_SCHEMA_VERSIONS = {1}


# --- connection helpers (mirrors export_playlists.py) -----------------------

def connect_via_token(baseurl: str, token: str) -> PlexServer:
    return PlexServer(baseurl, token)


def connect_via_pin_login(server_name: str = None) -> PlexServer:
    """
    See export_playlists.py's connect_via_pin_login for why this uses
    MyPlexPinLogin rather than a bare MyPlexAccount() call.
    """
    pinlogin = MyPlexPinLogin(oauth=True)
    print(f"Opening {pinlogin.oauthUrl()} in your browser — sign in and approve access.")
    pinlogin.run(timeout=120)
    pinlogin.waitForLogin()

    if not pinlogin.token:
        raise RuntimeError("Login timed out or was not approved. Please try again.")

    account = MyPlexAccount(token=pinlogin.token)
    resources = [r for r in account.resources() if r.provides == "server"]

    if not resources:
        raise RuntimeError("No Plex Media Servers found on this account.")

    if server_name:
        matches = [r for r in resources if r.name == server_name]
        if not matches:
            raise RuntimeError(f"No server named '{server_name}' found.")
        resource = matches[0]
    elif len(resources) == 1:
        resource = resources[0]
    else:
        names = ", ".join(r.name for r in resources)
        raise RuntimeError(
            f"Multiple servers found ({names}); pass server_name to disambiguate."
        )

    return resource.connect()


# --- loading exported files (handles both 'separate' and 'combined' shapes) -

def load_playlist_docs(path: Path) -> list[dict]:
    """
    Normalize either export shape into a flat list of playlist docs.
    A 'separate' file has a top-level 'items' key (one playlist).
    A 'combined' file has a top-level 'playlists' key (many playlists).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported schema_version {data.get('schema_version')!r} in {path}"
        )

    if "playlists" in data:
        return data["playlists"]
    elif "items" in data:
        return [data]
    else:
        raise ValueError(f"{path} doesn't match either known export shape.")


# --- building a lookup index of the target server's library -----------------

@dataclass
class LibraryIndex:
    by_guid: dict = field(default_factory=dict)          # any guid -> item
    movies_by_title_year: dict = field(default_factory=dict)   # (title, year) -> item
    episodes_by_key: dict = field(default_factory=dict)  # (show, season, ep) -> item


def build_library_index(server: PlexServer) -> LibraryIndex:
    """
    Walk the target server's movie and show libraries once, building lookup
    tables so matching is O(1) per item instead of a search-per-item.
    """
    idx = LibraryIndex()

    for section in server.library.sections():
        if section.type == "movie":
            for movie in section.all():
                idx.by_guid[movie.guid] = movie
                for g in getattr(movie, "guids", []):
                    idx.by_guid[g.id] = movie
                idx.movies_by_title_year[(movie.title.lower(), movie.year)] = movie

        elif section.type == "show":
            for episode in section.search(libtype="episode"):
                idx.by_guid[episode.guid] = episode
                for g in getattr(episode, "guids", []):
                    idx.by_guid[g.id] = episode
                key = (
                    (episode.grandparentTitle or "").lower(),
                    episode.parentIndex,
                    episode.index,
                )
                idx.episodes_by_key[key] = episode

    return idx


# --- matching -----------------------------------------------------------

def match_item(entry: dict, idx: LibraryIndex):
    """
    Try GUID match first (exact, survives title/metadata edits), then fall
    back to title+year (movies) or show/season/episode (episodes).
    Returns the matched plexapi item, or None if nothing matched.
    """
    for guid in entry.get("external_guids", []):
        if guid in idx.by_guid:
            return idx.by_guid[guid]

    if entry.get("plex_guid") in idx.by_guid:
        return idx.by_guid[entry["plex_guid"]]

    if entry["type"] == "movie":
        key = (entry["title"].lower(), entry.get("year"))
        return idx.movies_by_title_year.get(key)

    if entry["type"] == "episode":
        key = (
            (entry.get("show_title") or "").lower(),
            entry.get("season_number"),
            entry.get("episode_number"),
        )
        return idx.episodes_by_key.get(key)

    return None


@dataclass
class ImportResult:
    playlist_title: str
    matched: list = field(default_factory=list)
    unmatched: list = field(default_factory=list)  # original entries that didn't match
    created: bool = False
    skipped_reason: str = None


# --- import ---------------------------------------------------------------

def import_playlist(
    server: PlexServer,
    doc: dict,
    idx: LibraryIndex,
    on_conflict: str = "skip",  # 'skip' | 'replace' | 'rename'
) -> ImportResult:
    """Import a single playlist doc into the target server."""
    result = ImportResult(playlist_title=doc["playlist_title"])

    for entry in doc["items"]:
        matched = match_item(entry, idx)
        if matched:
            result.matched.append(matched)
        else:
            result.unmatched.append(entry)

    if not result.matched:
        result.skipped_reason = "No items matched on the target server."
        return result

    title = doc["playlist_title"]
    existing = next((p for p in server.playlists() if p.title == title), None)

    if existing:
        if on_conflict == "skip":
            result.skipped_reason = f"Playlist '{title}' already exists (skipped)."
            return result
        elif on_conflict == "replace":
            existing.delete()
        elif on_conflict == "rename":
            title = f"{title} (imported)"

    server.createPlaylist(title, items=result.matched)
    result.created = True
    return result


def import_from_file(
    server: PlexServer,
    path: Path,
    idx: LibraryIndex,
    selected_titles: list[str] = None,  # None = import everything in the file
    on_conflict: str = "skip",
) -> list[ImportResult]:
    """
    Entry point for both CLI and GUI. For a combined file, selected_titles
    lets the caller (e.g. a GUI checklist) restore only some playlists.
    """
    docs = load_playlist_docs(path)

    if selected_titles is not None:
        wanted = set(selected_titles)
        docs = [d for d in docs if d["playlist_title"] in wanted]

    return [import_playlist(server, doc, idx, on_conflict=on_conflict) for doc in docs]


def print_report(results: list[ImportResult]):
    for r in results:
        if r.skipped_reason:
            print(f"⚠️  {r.playlist_title}: {r.skipped_reason}")
            continue

        print(f"✅ {r.playlist_title}: {len(r.matched)} matched, {len(r.unmatched)} unmatched")
        for entry in r.unmatched:
            label = entry["title"] if entry["type"] == "movie" else (
                f"{entry.get('show_title')} S{entry.get('season_number')}E{entry.get('episode_number')} - {entry['title']}"
            )
            print(f"    - {label}")


def main():
    parser = argparse.ArgumentParser(description="Import Plex video playlists from JSON.")
    parser.add_argument("--baseurl", help="e.g. http://localhost:32400")
    parser.add_argument("--token", help="X-Plex-Token (use with --baseurl)")
    parser.add_argument("--server-name", help="Server name (use with PIN login, if multiple servers)")
    parser.add_argument("--input", required=True, help="Path to an exported JSON file")
    parser.add_argument(
        "--select",
        help="Comma-separated playlist titles to import from a combined file "
             "(default: import all playlists in the file)",
    )
    parser.add_argument(
        "--on-conflict",
        choices=["skip", "replace", "rename"],
        default="skip",
        help="What to do if a playlist with the same title already exists",
    )
    args = parser.parse_args()

    if args.baseurl and args.token:
        server = connect_via_token(args.baseurl, args.token)
    else:
        server = connect_via_pin_login(args.server_name)

    print("Indexing target server library...")
    idx = build_library_index(server)

    selected = args.select.split(",") if args.select else None
    results = import_from_file(
        server, Path(args.input), idx, selected_titles=selected, on_conflict=args.on_conflict
    )
    print_report(results)


if __name__ == "__main__":
    main()
