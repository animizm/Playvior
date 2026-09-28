# Privacy Policy

Last updated: 2026-09-27

Playvior is a local desktop tool. This policy explains what data it
handles, since it does still talk to Plex's own services in order to work.

## Summary

- Playvior collects **no telemetry, analytics, or usage data** of any kind.
- Playvior does **not** have its own server, and the people who develop it
  do not receive, see, or store any of your data.
- The only network communication Playvior performs is directly between
  your computer and **Plex's own services** (plex.tv and your Plex Media
  Server), in order to sign you in and read/write playlists on your
  behalf.
- Exported playlist files are plain JSON, written only to the folder you
  choose, and stay on your computer unless you move or share them
  yourself.

## Signing in

Playvior signs you in using Plex's own PIN-based OAuth flow
(`MyPlexPinLogin`, part of the official `plexapi` library): it opens a
page at `plex.tv` in your browser, you sign in and approve access there,
and Plex hands back an access token. Playvior never sees, asks for, or
stores your Plex username or password — that entire exchange happens on
Plex's own site, governed by
[Plex's own privacy policy](https://www.plex.tv/about/privacy-legal/).

The access token Plex returns is held in memory for the running session
only. Playvior does not write it to disk, a config file, or anywhere else
— close the app (or the terminal, for the CLI scripts) and it's gone. You
sign in again the next time you run it.

If you instead connect using a server URL and an existing token you supply
yourself (`--baseurl`/`--token` on the command-line scripts), that token is
used only to make the connection for that run and is likewise never
written to disk by Playvior.

## What data Playvior reads and writes

- **Reads:** your list of Plex servers, the video playlists on a server
  you connect to, and (for import) the library contents of the target
  server, so it can match items by ID/title.
- **Writes:** new or updated playlists on a Plex server you're connected
  to (only when you click Export/Import or run the corresponding CLI
  command), and exported `.json` files to the output folder you choose.

All of this data — server contents, playlist metadata, exported files —
stays between your computer and your Plex server(s). Playvior does not
relay, log, or transmit any of it anywhere else.

## Exported files

An exported playlist file contains the playlist's title and summary, and
for each item: its title, year/type, Plex and external (IMDb/TMDb/TVDB)
GUIDs, duration, and (for episodes) show/season/episode number. It does
not contain your account credentials, access token, or any personal
account information. Treat an exported file like any other file on your
computer — Playvior has no say over what you do with it once it's
written, including if you choose to share it with someone else.

## Third parties

Playvior itself does not integrate with, or send data to, any third party
other than the Plex service you explicitly connect it to. It has no
analytics SDK, crash reporter, ad network, or similar embedded in it.

## Changes to this policy

If Playvior's data handling ever changes (for example, if a future version
adds an optional update-check), this document will be updated alongside
that change and noted in [CHANGELOG.md](CHANGELOG.md).

## Contact

Questions about this policy can be raised as an issue on the project's
GitHub page.
