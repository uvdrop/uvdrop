; uvdrop Inno Setup script
; Build with: powershell -File installer\build.ps1
; Docs: installer\PACKAGING.md
;
; Goal: ship Setup.exe (Apps & Features) instead of a bare PyInstaller exe.

#define MyAppName "uvdrop"
; Keep in sync with src/uvdrop/version.py (build.ps1 overrides this at build time).
#define MyAppVersion "0.10.1"
#define MyAppPublisher "uvdrop"
#define MyAppURL "https://uvdrop.github.io/uvdrop/"
#define MyAppExeName "uvdrop.exe"

[Setup]
AppId={{8F3C2B1A-9D47-4E6F-A1B2-C3D4E5F60718}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://github.com/uvdrop/uvdrop/issues
AppUpdatesURL=https://github.com/uvdrop/uvdrop/releases
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
InfoBeforeFile=
OutputDir=output
OutputBaseFilename=uvdrop-{#MyAppVersion}-setup
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
; Close previous instance on upgrade when possible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加アイコン:"; Flags: unchecked

[Files]
; Built by installer/build.ps1 (PyInstaller onedir)
Source: "..\dist\uvdrop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Bundled uv (fetched by installer/fetch-uv.ps1)
Source: "..\resources\tools\windows-x64\uv.exe"; DestDir: "{app}\tools"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\アンインストール {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} を起動"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
