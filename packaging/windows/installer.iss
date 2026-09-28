; Inno Setup script for Playvior.
;
; Built by CI (see .github/workflows/build-installers.yml), which first runs
; PyInstaller to produce dist\Playvior.exe, then compiles this script with:
;
;   iscc /DMyAppVersion=<version> packaging\windows\installer.iss
;
; To build locally on Windows instead:
;   1. pip install -r requirements.txt pyinstaller
;   2. pyinstaller --noconfirm --onefile --windowed --name Playvior ^
;        --icon assets\playvior.ico --add-data "assets;assets" gui.py
;   3. Install Inno Setup (https://jrsoftware.org/isinfo.php), then either
;      open this file in the Inno Setup Compiler and click Build, or run
;      "iscc /DMyAppVersion=0.1.0 packaging\windows\installer.iss" from a
;      "Developer" command prompt with iscc.exe on PATH.
; The compiled installer is written to dist\installer\PlayviorSetup-<version>.exe.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "Playvior"
#define MyAppPublisher "Playvior contributors"
#define MyAppURL "https://github.com/"

[Setup]
AppId={{B7B6C6C0-6E29-4A0E-9A3B-5B0B7F6D9B3A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; The GUI executable is produced one directory up (repo root's dist\), and
; this script itself lives in packaging\windows\, so paths below are
; relative to the repo root, resolved via SourcePath.
SourceDir=..\..
OutputDir=dist\installer
OutputBaseFilename=PlayviorSetup-{#MyAppVersion}
SetupIconFile=assets\playvior.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=LICENSE
UninstallDisplayIcon={app}\Playvior.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\Playvior.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Playvior.exe"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Playvior.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Playvior.exe"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
