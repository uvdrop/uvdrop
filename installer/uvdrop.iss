; uvdrop Inno Setup script
; Requires: Inno Setup 6+, and a built payload under dist\uvdrop\
; Build payload first (see build.ps1), then compile this .iss
;
; Goal: ship Setup.exe (Apps & Features) instead of a bare PyInstaller exe,
; which tends to trip AV heuristics less often when also Authenticode-signed.

#define MyAppName "uvdrop"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "uvdrop"
#define MyAppURL "https://uvdrop.github.io/uvdrop/"
#define MyAppExeName "uvdrop.exe"

[Setup]
AppId={{8F3C2B1A-9D47-4E6F-A1B2-C3D4E5F60718}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://github.com/uvdrop/uvdrop/issues
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=output
OutputBaseFilename=uvdrop-{#MyAppVersion}-setup
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

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加アイコン:"; Flags: unchecked

[Files]
; Built by installer/build.ps1 (PyInstaller onedir)
Source: "..\dist\uvdrop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Bundled uv (place before packaging)
Source: "..\resources\tools\windows-x64\uv.exe"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} を起動"; Flags: nowait postinstall skipifsilent
