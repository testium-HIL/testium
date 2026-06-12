; Inno Setup script: wraps the PyInstaller testium.exe into a per-user installer.
; Build with Inno Setup 6: ISCC.exe testium.iss (or ./build.ps1).

#define MyAppName "Testium"
#define MyAppExeName "testium.exe"
#define MyAppPublisher "Testium"
#define MyAppURL "https://github.com/"

; Read version from src/VERSION so the installer never drifts from the build.
#define VerFile FileOpen("..\..\src\VERSION")
#define MyAppVersion Trim(FileRead(VerFile))
#expr FileClose(VerFile)
#if MyAppVersion == ""
  #error Could not read version from ..\..\src\VERSION
#endif

[Setup]
; Version-scoped AppId: each version is a distinct app, installable side-by-side.
AppId={{B7E6F1C2-9A4D-4E3B-8F71-7C2D5A6E0B14}_{#MyAppVersion}
AppName={#MyAppName} {#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
WizardStyle=modern
; Per-version install dir so versions never overwrite each other.
DefaultDirName={autopf}\{#MyAppName}\{#MyAppVersion}
; Shared "Testium" Start Menu folder; shortcuts below are named per version.
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\testium.ico
DisableProgramGroupPage=yes
; Per-user install, no admin ever: installs under %LOCALAPPDATA%, no UAC prompt.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=testium-{#MyAppVersion}-setup
SetupIconFile=..\testium.ico
Compression=lzma2/max
SolidCompression=yes
; Tell Explorer to refresh the environment after a PATH change.
ChangesEnvironment=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
; PATH off by default: the exe is windowed (console=False), so CLI shows no output.
Name: "addtopath"; Description: "Ajouter Testium au PATH (usage en ligne de commande)"; Flags: unchecked

[Files]
Source: "..\pyinstaller\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Ship the .ico so shortcuts/uninstall reference it directly, not the embedded one.
Source: "..\testium.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Per-version names so each install shows separately in the Start Menu.
Name: "{group}\{#MyAppName} {#MyAppVersion}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\testium.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName} {#MyAppVersion}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} {#MyAppVersion}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\testium.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
const
  EnvKey = 'Environment';

// True if Param is not already a full segment of the per-user PATH.
function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
end;

// On install: append {app} to the per-user PATH if the task is selected.
procedure CurStepChanged(CurStep: TSetupStep);
var
  Path: string;
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('addtopath') and NeedsAddPath(ExpandConstant('{app}')) then
    begin
      if not RegQueryStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Path) then
        Path := '';
      if (Path <> '') and (Copy(Path, Length(Path), 1) <> ';') then
        Path := Path + ';';
      Path := Path + ExpandConstant('{app}');
      RegWriteStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Path);
    end;
  end;
end;

// On uninstall: strip {app} back out of the per-user PATH.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Path, AppDir, Segment: string;
  P: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    if RegQueryStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Path) then
    begin
      AppDir := ExpandConstant('{app}');
      Segment := ';' + AppDir;
      P := Pos(Uppercase(Segment), Uppercase(Path));
      if P > 0 then
        Delete(Path, P, Length(Segment))
      else
      begin
        P := Pos(Uppercase(AppDir) + ';', Uppercase(Path));
        if P = 1 then
          Delete(Path, 1, Length(AppDir) + 1);
      end;
      RegWriteStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Path);
    end;
  end;
end;
