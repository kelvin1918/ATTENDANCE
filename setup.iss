#define AppName "BatStateU Attendance System"
#define AppVersion "1.0.0"
#define AppPublisher "Batangas State University"
#define AppExeName "AttendanceStation.exe"

[Setup]
AppId={{B4A7E2C1-9F3D-4A8B-BE12-7C6D5E4F3A2B}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\BatStateU Attendance
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename=BatStateU_Attendance_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
MinVersion=10.0
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"

[Files]
Source: "dist\AttendanceStation\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\faces"
Name: "{app}\uploads"
Name: "{app}\uploads\signatures"
Name: "{app}\uploads\photos"
Name: "{app}\pdf"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent
