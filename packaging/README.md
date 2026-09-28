# Building installers

Playvior's GUI can be packaged into a native installer for Windows, macOS,
and Linux, using [PyInstaller](https://pyinstaller.org/) plus a small
OS-specific packaging step. The easiest way to get all three is to let CI do
it (see below) — a GUI binary can only be built on the OS it targets, so
producing all three from one machine isn't possible.

## Automated (recommended): GitHub Actions

`.github/workflows/build-installers.yml` builds all three installers on
GitHub-hosted Windows/macOS/Linux runners.

- **Push a tag** like `v0.1.0` to build and attach installers to a new
  GitHub Release automatically:

  ```bash
  git tag v0.1.0
  git push origin v0.1.0
  ```

- **Or trigger it manually** without tagging, from the repo's Actions tab →
  "Build installers" → "Run workflow". The three installers are then
  attached to that run as downloadable artifacts instead of a release.

The version number embedded in filenames and the Windows installer comes
from the top-level `VERSION` file — bump that alongside `CHANGELOG.md` when
cutting a release.

## Building locally

You only need the steps for your own OS.

### Windows → `PlayviorSetup-<version>.exe`

1. `pip install -r requirements.txt pyinstaller`
2. Build the executable:
   ```powershell
   pyinstaller --noconfirm --onefile --windowed --name Playvior `
     --icon assets\playvior.ico --add-data "assets;assets" gui.py
   ```
3. Install [Inno Setup](https://jrsoftware.org/isinfo.php), then compile
   `packaging\windows\installer.iss` — either open it in the Inno Setup
   Compiler GUI and click Build, or from a command prompt with `iscc.exe`
   on `PATH`:
   ```powershell
   iscc /DMyAppVersion=0.1.0 packaging\windows\installer.iss
   ```
   The installer is written to `dist\installer\PlayviorSetup-0.1.0.exe`.

The installer isn't code-signed (that needs a paid code-signing
certificate), so Windows SmartScreen may warn on first run; users can click
"More info" → "Run anyway".

### macOS → `Playvior-<version>.dmg`

1. `pip install -r requirements.txt pyinstaller`
2. Generate an `.icns` from the existing PNGs (one-time, or whenever the
   icon changes):
   ```bash
   ICONSET=Playvior.iconset
   mkdir "$ICONSET"
   cp assets/playvior_16.png  "$ICONSET/icon_16x16.png"
   cp assets/playvior_32.png  "$ICONSET/icon_16x16@2x.png"
   cp assets/playvior_32.png  "$ICONSET/icon_32x32.png"
   cp assets/playvior_64.png  "$ICONSET/icon_32x32@2x.png"
   cp assets/playvior_128.png "$ICONSET/icon_128x128.png"
   cp assets/playvior_256.png "$ICONSET/icon_128x128@2x.png"
   cp assets/playvior_256.png "$ICONSET/icon_256x256.png"
   cp assets/playvior_256.png "$ICONSET/icon_256x256@2x.png"
   iconutil -c icns "$ICONSET" -o assets/Playvior.icns
   ```
3. Build the `.app`:
   ```bash
   pyinstaller --noconfirm --windowed --name Playvior \
     --icon assets/Playvior.icns --add-data "assets:assets" gui.py
   ```
4. Package it as a `.dmg`:
   ```bash
   STAGING=dist/dmg-staging
   mkdir -p "$STAGING"
   cp -R dist/Playvior.app "$STAGING/"
   ln -s /Applications "$STAGING/Applications"
   hdiutil create -volname Playvior -srcfolder "$STAGING" \
     -ov -format UDZO dist/Playvior-0.1.0.dmg
   ```

The app isn't signed or notarized (that needs a paid Apple Developer
account), so Gatekeeper will call it "unidentified developer" on first
launch; users right-click the app → Open → Open, once, to bypass that.

### Linux → `Playvior-<version>-x86_64.AppImage`

1. Make sure the Tk binding matches your Python's version, e.g.
   `sudo apt install python3-tk` (Debian/Ubuntu) or the equivalent for your
   distro — otherwise PyInstaller silently drops `tkinter` from the build
   and the binary won't start.
2. `pip install -r requirements.txt pyinstaller`
3. Build the executable:
   ```bash
   pyinstaller --noconfirm --onefile --name playvior \
     --add-data "assets:assets" gui.py
   ```
4. Assemble the AppDir and build the AppImage:
   ```bash
   mkdir -p AppDir/usr/bin
   cp dist/playvior AppDir/usr/bin/playvior
   chmod +x AppDir/usr/bin/playvior
   cp assets/playvior_256.png AppDir/playvior.png
   cp packaging/linux/playvior.desktop AppDir/playvior.desktop
   cp packaging/linux/AppRun AppDir/AppRun
   chmod +x AppDir/AppRun

   curl -sSL -o appimagetool.AppImage \
     https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
   chmod +x appimagetool.AppImage
   ARCH=x86_64 ./appimagetool.AppImage AppDir dist/Playvior-0.1.0-x86_64.AppImage
   ```

The resulting `.AppImage` is a single file: users `chmod +x` it and
double-click (or run) it directly — no install step, no root required.
