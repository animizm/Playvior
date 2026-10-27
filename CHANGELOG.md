# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-10-26

### Changed

- Rounded corners on buttons and frames are now drawn with CustomTkinter's
  default antialiased glyph rendering instead of forced canvas polygons, so
  they are smooth and even instead of stair-stepped. The dropdown chevron and
  checkbox checkmark keep their own pinned drawing methods.
- Export tab: Output Folder and Export Mode are now separate sections, with
  Export Mode below Output Folder.
- The window's minimum size is now measured from the layout itself (taller on
  the Import tab) instead of a fixed value, so the log console at the bottom
  is no longer squeezed when the window is made small.

### Fixed

- Fixed a crash after connecting to a server (Windows "CreateDIBSection"
  error, with duplicated Export/Import tab buttons). The scrollbar-sync code
  re-triggered itself on every child-widget resize until Windows ran out of
  graphics handles. It now reacts only to the window's own resize, debounces
  the check, and can no longer re-enter itself.
- Fixed the playlist list ballooning to fill the window, pushing the options
  and log console out of view (and eventually raising the same "CreateDIBSection"
  error) when the window was resized. Hiding and re-showing the list's
  scrollbar compounded its padding by the display scale factor each time; the
  saved layout is now restored exactly.
- Fixed the list scrollbar flickering on and off, and often showing the wrong
  state. Whether it is needed is now judged against the list's fixed height
  rather than its own current size, and the scrollbar no longer asks for extra
  height of its own.

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

[0.1.1]: https://github.com/animizm/Playvior/releases/tag/v0.1.1
[0.1.0]: https://github.com/animizm/Playvior/releases/tag/v0.1.0
