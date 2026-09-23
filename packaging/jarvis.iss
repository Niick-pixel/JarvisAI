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

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\build\dist\Jarvis\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Jarvis.exe"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\Jarvis.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Jarvis.exe"; Description: "Start Jarvis now"; Flags: nowait postinstall skipifsilent
