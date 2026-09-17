; Instalador de CalandriaSys (Inno Setup). Adaptado del installer.iss del repo
; DynamicSepticSystem original: mismo esquema, otro AppId y otra marca.
;
; Compilar:  ISCC.exe installer.iss /DMyAppVersion=1.9.4.8
; Sin /DMyAppVersion usa la version del .exe compilado en bin\Release.
;
; Ojo con [Files]: excluye secrets.config y los *.example a proposito (ver abajo).

#define MyAppName "CalandriaSys"
#define MyAppPublisher "Calandria Residencial"
#define MyAppExeName "DynamicSepticSystem.exe"
#define MyAppSourceDir "DynamicSepticSystem\bin\Release"
#ifndef MyAppVersion
  #define MyAppVersion GetVersionNumbersString(MyAppSourceDir + "\" + MyAppExeName)
#endif

[Setup]
; GUID fijo: NO cambiar entre versiones (identifica la app para que "instalar
; encima" actualice en vez de duplicar). Distinto del de Pilaris a proposito:
; son dos productos que pueden convivir en la misma maquina.
AppId={{3F1D9A64-5B27-4C0E-9A31-8D64C2F7E5B1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CalandriaSys
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=CalandriaSysSetup-v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
; No pide elevacion salvo que Program Files la requiera (la pide Windows solo).
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"

[Files]
; Todo bin\Release EXCEPTO secrets.config y los *.example: ese archivo trae el
; token personal de GitHub del desarrollador que compilo el instalador, y la
; app funciona sin el (solo baja el limite de peticiones a la API de GitHub).
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "secrets.config,secrets.config.example,connectionStrings.config,connectionStrings.config.example,*.pdb,*.xml,*.cs,*.log"
; connectionStrings.config SI se necesita (las pantallas que aun no migran a la
; Web API hacen SQL directo), pero NO el del desarrollador: el de bin\Release
; apunta a localhost\SQLEXPRESS y en la maquina del cliente cuelga ~30 s al
; entrar al panel. Se empaqueta la cadena de produccion.
Source: "connectionStrings.release.config"; DestDir: "{app}"; DestName: "connectionStrings.config"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; Flags: nowait postinstall skipifsilent
