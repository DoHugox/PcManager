; Inno Setup Script for PcManager (Windows Server Guardian)
; Creates a standard Windows Installer Wizard (PcManager_Setup.exe) with Icon and Shortcuts

#define MyAppName "PcManager"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DoHugox"
#define MyAppURL "https://github.com/DoHugox/PcManager"
#define MyAppExeName "PcManager.exe"

[Setup]
AppId={{D37E848B-2F38-4C3D-8827-01D78F4A8001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=dist
OutputBaseFilename=PcManager_Setup
SetupIconFile=assets\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\assets\app.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Tự động khởi động cùng Windows khi bật máy (Chạy ngầm bảo vệ 24/7)"; GroupDescription: "Thiết lập hệ thống:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\app.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "assets\app.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "bios_helper.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "HUONG_DAN_CAI_DAT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app.ico"
Name: "{autoprograms}\Dashboard Web"; Filename: "http://localhost:8888"; IconFilename: "{app}\assets\app.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app.ico"; Tasks: desktopicon
Name: "{autodesktop}\PcManager Dashboard"; Filename: "http://localhost:8888"; IconFilename: "{app}\assets\app.ico"; Tasks: desktopicon

[Run]
; Cấu hình tự khởi động vào Task Scheduler nếu người dùng chọn
Filename: "schtasks.exe"; Parameters: "/create /tn ""{#MyAppName}"" /tr """"{app}\{#MyAppExeName}"""" /sc onstart /ru ""SYSTEM"" /rl HIGHEST /f"; Flags: runhidden; Tasks: autostart
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/delete /tn ""{#MyAppName}"" /f"; Flags: runhidden
