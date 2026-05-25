; adv7YT Inno Setup Script
; Build: iscc installer\adv7YT.iss
; Requires: publish/portable/adv7YT.exe to exist (run dotnet publish first)

[Setup]
AppName=adv7YT
AppVersion=0.1.0
AppPublisher=AOPS
AppPublisherURL=https://github.com/aops-dev
AppSupportURL=https://github.com/aops-dev/adv7YT
DefaultDirName={autopf}\adv7YT
DefaultGroupName=adv7YT
AllowNoIcons=yes
OutputDir=..\publish\installer
OutputBaseFilename=adv7YT-0.1.0-setup
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
UninstallDisplayIcon={app}\adv7YT.exe
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Files]
Source: "..\publish\portable\adv7YT.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\adv7YT";      Filename: "{app}\adv7YT.exe"
Name: "{group}\Uninstall adv7YT"; Filename: "{uninstallexe}"
Name: "{autodesktop}\adv7YT"; Filename: "{app}\adv7YT.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\adv7YT.exe"; Description: "Launch adv7YT now"; Flags: nowait postinstall skipifsilent
