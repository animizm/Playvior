# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-27

Initial public release.

### Added

- Command-line scripts for exporting (`export_playlists.py`) and importing
  (`import_playlists.py`) Plex video playlists as portable JSON files.
  - Matches items on import by external GUID (IMDb/TMDb/TVDB) first,
    falling back to title/year (movies) or show/season/episode (episodes).
  - Export as one file per playlist, or a single combined backup file.
  - Configurable conflict handling on import: skip, replace, or duplicate
    a playlist that already exists on the target server.
  - Plex sign-in via either the PIN/OAuth browser flow or a direct
    server URL + token.
- Desktop GUI (`gui.py`, built with CustomTkinter) as a friendlier front
  end onto the same export/import logic:
  - Sign in with Plex, choose a server, and browse its video playlists.
  - Export and Import tabs with per-playlist checklists.
  - Export/Import action buttons that enable only once a server is
    connected, playlists are loaded, and at least one is checked; a
    pulsing blue outline highlights the button once it's ready to go.
  - Custom application icon and window branding.
- Cross-platform support: Linux, Windows, and macOS.
- Packaged installer builds for Windows (`PlayviorSetup-<version>.exe` via
  Inno Setup), macOS (`Playvior-<version>.dmg`), and Linux
  (`Playvior-<version>-x86_64.AppImage`), built automatically by a GitHub
  Actions workflow whenever a `v*` tag is pushed and attached to the
  resulting release. See `packaging/README.md` for details and local build
  instructions.

<!--
Once this is pushed to GitHub and tagged, you can turn "[0.1.0]" above into
a link by adding a line like:
[0.1.0]: https://github.com/<your-username>/Playvior/releases/tag/v0.1.0
-->
