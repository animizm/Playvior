"""
Export Plex video playlists to portable JSON files.

Requires: pip install plexapi
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin

SCHEMA_VERSION = 1


def connect_via_token(baseurl: str, token: str) -> PlexServer:
    """Connect directly if the user already has a server URL + token."""
    return PlexServer(baseurl, token)


def connect_via_pin_login(server_name: str = None) -> PlexServer:
    """
    Interactive PIN-based OAuth login — this is what the GUI will eventually
    wrap. No manual token-copying required from the end user.

    MyPlexAccount() with no arguments does NOT do this on its own — it
    expects a username/password or an existing token. The actual PIN/OAuth
    flow lives in MyPlexPinLogin: it opens plex.tv/link in your browser
    with a 4-character code already filled in, and once you approve it
    there, it hands back a token we use to build a real MyPlexAccount.
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


def _item_to_dict(item) -> dict:
    """
    Convert a single Plex library item (movie or episode) into our
    portable JSON representation. We collect ALL available external
    GUIDs (IMDb/TMDb/TVDB), not just Plex's internal one, since those
    are the stable identifiers across servers and metadata agent changes.
    """
    # item.guids is a list of Guid objects like:
    #   Guid(id='imdb://tt1234567'), Guid(id='tmdb://12345'), Guid(id='tvdb://6789')
    external_guids = [g.id for g in getattr(item, "guids", [])]

    entry = {
        "title": item.title,
        "year": getattr(item, "year", None),
        "type": item.type,  # 'movie' or 'episode'
        "plex_guid": item.guid,  # Plex's own internal guid (best-effort match only)
        "external_guids": external_guids,
        "duration_ms": getattr(item, "duration", None),
    }

    # Episodes need extra context for fuzzy matching on import, since
    # title alone ("Pilot") is nowhere near unique enough.
    if item.type == "episode":
        entry["show_title"] = getattr(item, "grandparentTitle", None)
        entry["season_number"] = getattr(item, "parentIndex", None)
        entry["episode_number"] = getattr(item, "index", None)

    return entry


def export_playlist(playlist, source_server_name: str) -> dict:
    """Build the full export document for one playlist."""
    items = [_item_to_dict(item) for item in playlist.items()]

    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_from_server": source_server_name,
        "playlist_title": playlist.title,
        "playlist_summary": playlist.summary or "",
        "item_count": len(items),
        "items": items,
    }


def _safe_filename(title: str) -> str:
    return "".join(
        c if c.isalnum() or c in " -_" else "_" for c in title
    ).strip()


def get_video_playlists(server: PlexServer):
    """Fetch every VIDEO playlist on the server, explicitly skipping audio/music."""
    return [p for p in server.playlists() if p.playlistType == "video"]


def export_separate_files(
    playlists, server: PlexServer, output_dir: Path
) -> list[Path]:
    """One JSON file per playlist. Best for selective import/sharing."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for playlist in playlists:
        doc = export_playlist(playlist, server.friendlyName)
        out_path = output_dir / f"{_safe_filename(playlist.title)}.json"

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

        print(f"Exported '{playlist.title}' ({doc['item_count']} items) -> {out_path}")
        written.append(out_path)

    return written


def export_combined_file(
    playlists, server: PlexServer, output_dir: Path, filename: str = "playlists_export.json"
) -> Path:
    """Single JSON file containing all playlists. Best for a full backup."""
    output_dir.mkdir(parents=True, exist_ok=True)

    docs = [export_playlist(p, server.friendlyName) for p in playlists]
    combined = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_from_server": server.friendlyName,
        "playlist_count": len(docs),
        "playlists": docs,
    }

    out_path = output_dir / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    total_items = sum(d["item_count"] for d in docs)
    print(f"Exported {len(docs)} playlists ({total_items} items total) -> {out_path}")
    return out_path


def export_video_playlists(
    server: PlexServer, output_dir: Path, mode: str = "separate"
):
    """
    Single entry point both the CLI and the future GUI should call.
    mode: 'separate' (one file per playlist) or 'combined' (one file, all playlists).
    Returns the file(s) written (a list for 'separate', a single Path for 'combined').
    """
    if mode not in ("separate", "combined"):
        raise ValueError(f"Unknown mode: {mode!r} (expected 'separate' or 'combined')")

    playlists = get_video_playlists(server)
    if not playlists:
        print("No video playlists found on this server.")
        return [] if mode == "separate" else None

    if mode == "separate":
        return export_separate_files(playlists, server, output_dir)
    else:
        return export_combined_file(playlists, server, output_dir)


def _prompt_for_mode() -> str:
    """Used only when --mode isn't passed on the command line."""
    while True:
        choice = input(
            "Export mode — (1) one file per playlist, or (2) single combined file? [1/2]: "
        ).strip()
        if choice == "1":
            return "separate"
        if choice == "2":
            return "combined"
        print("Please enter 1 or 2.")


def main():
    parser = argparse.ArgumentParser(description="Export Plex video playlists to JSON.")
    parser.add_argument("--baseurl", help="e.g. http://localhost:32400")
    parser.add_argument("--token", help="X-Plex-Token (use with --baseurl)")
    parser.add_argument("--server-name", help="Server name (use with PIN login, if multiple servers)")
    parser.add_argument("--output", default="./exported_playlists", help="Output directory")
    parser.add_argument(
        "--mode",
        choices=["separate", "combined"],
        help="separate = one file per playlist; combined = single file with all playlists. "
             "If omitted, you'll be prompted interactively.",
    )
    args = parser.parse_args()

    if args.baseurl and args.token:
        server = connect_via_token(args.baseurl, args.token)
    else:
        server = connect_via_pin_login(args.server_name)

    mode = args.mode or _prompt_for_mode()
    export_video_playlists(server, Path(args.output), mode=mode)


if __name__ == "__main__":
    main()
