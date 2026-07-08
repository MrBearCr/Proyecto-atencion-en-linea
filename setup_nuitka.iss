#define MyAppName "Casapro Nexus"
#define MyAppVersion "1.7.3"
#define MyAppPublisher "rafael3gn@gmail.com"
#define MyAppURL "rafael3gn@gmail.com"
#define MyAppExeName "Casapro Nexus.exe"
#define MyUpdaterExeName "nexus_updater.exe"
#define NuitkaStandaloneDir "app.dist"

[Setup]
; A unique AppId is required for each application.
; Mantenemos el mismo GUID para que reconozca instalaciones previas y las actualice
AppId={{228B5B49-524C-4328-8A33-524787258525}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
SetupIconFile=pal\ui\image.ico
AllowNoIcons=no
; The installer will be created in the 'dist' folder.
OutputDir=dist
OutputBaseFilename=NEXUS-Setup-v{#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked 

[Files]
; ----------------------------------------------------------------------------------
; CONFIGURACIÓN PARA NUITKA STANDALONE
; Nuitka en modo Standalone genera una carpeta "app.dist" con el ejecutable y DLLs.
; Empaquetar el modo Standalone con Inno Setup es MEJOR que usar el modo --onefile 
; porque la app inicia instantáneamente (no tiene que extraerse en Temp cada vez).
; ----------------------------------------------------------------------------------

; Incluir el ejecutable principal primero
Source: "{#NuitkaStandaloneDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion restartreplace
; Incluir el actualizador externo con manifiesto de Administrador
Source: "{#NuitkaStandaloneDir}\{#MyUpdaterExeName}"; DestDir: "{app}"; Flags: ignoreversion restartreplace
; Incluir todo el contenido recursivo de la carpeta app.dist
Source: "{#NuitkaStandaloneDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Scripts adicionales y recursos
Source: "pal\ui\image.ico"; DestDir: "{app}\pal\ui"; Flags: ignoreversion

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\pal\ui\image.ico";
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; Optional desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\pal\ui\image.ico";
