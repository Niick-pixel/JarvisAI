; Inno Setup script: wraps the PyInstaller folder into one JarvisSetup.exe.
;
; Per-user install into %LOCALAPPDATA%\Programs, so no administrator prompt: an app that runs
; entirely on loopback has no business asking for elevation. Your data lives separately in
; %LOCALAPPDATA%\Jarvis and is deliberately left alone by the uninstaller - removing the program
; should never delete your conversations or your memory.

#define AppName "Jarvis"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{6F0C4B5E-2A1D-4E8B-9C3F-7A5D1E2B4C60}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Jarvis (local-first)
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\build\installer
OutputBaseFilename=JarvisSetup
SetupIconFile=jarvis.ico
UninstallDisplayIcon={app}\Jarvis.exe
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
; An update runs this installer while Jarvis is open. It closes Jarvis itself first (see
; server/updates/install.py); this is the fallback for a window that did not.
CloseApplications=force
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\build\dist\Jarvis\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Microsoft's WebView2 bootstrapper (about 2MB). Jarvis draws its window with WebView2; Windows 11
; has it, some Windows 10 machines do not. Only run when it is missing - see [Run].
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedsWebView2

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Jarvis.exe"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\Jarvis.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft Edge WebView2..."; Flags: waituntilterminated; Check: NeedsWebView2
Filename: "{app}\Jarvis.exe"; Description: "Start Jarvis now"; Flags: nowait postinstall skipifsilent
; An in-app update runs silently with /RELAUNCH=1: reopen Jarvis on the new version.
Filename: "{app}\Jarvis.exe"; Flags: nowait; Check: Relaunch

[Code]
const
  WebView2Key = '\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasRuntime(Root: Integer; Key: String): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(Root, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0');
end;

{ Microsoft's documented check: the runtime's version under any of these three keys. }
function NeedsWebView2(): Boolean;
begin
  Result := not (HasRuntime(HKLM, 'SOFTWARE\WOW6432Node' + WebView2Key)
    or HasRuntime(HKLM, 'SOFTWARE' + WebView2Key)
    or HasRuntime(HKCU, 'Software' + WebView2Key));
end;

function Relaunch(): Boolean;
begin
  Result := ExpandConstant('{param:relaunch|0}') = '1';
end;
