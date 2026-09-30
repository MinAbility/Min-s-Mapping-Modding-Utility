    #ifndef AppVersion
    #define AppVersion "1.0.0"
    #endif

    #ifndef SourceDir
    #define SourceDir "dist\MinModdingMappingUtility"
    #endif

    [Setup]
    AppId={{4F5D6C28-8E29-4F24-86C6-3D8D4D763C2A}
    AppName=Min's Modding & Mapping Utility
    AppVersion={#AppVersion}
    AppPublisher=Min
    DefaultDirName={localappdata}\Programs\Min's Modding & Mapping Utility
    DefaultGroupName=Min's Modding & Mapping Utility
    DisableProgramGroupPage=yes
    PrivilegesRequired=lowest
    OutputDir=Output
    OutputBaseFilename=MinModdingMappingUtility-Setup
    SetupIconFile=MinModdingMappingUtility.ico
    Compression=lzma2
    SolidCompression=yes
    WizardStyle=modern
    ArchitecturesInstallIn64BitMode=x64compatible
    UninstallDisplayName=Min's Modding & Mapping Utility

    [Tasks]
    Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

    [Files]
    Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

    [Icons]
    Name: "{group}\Min's Modding & Mapping Utility"; Filename: "{app}\MinModdingMappingUtility.exe"; WorkingDir: "{app}"
    Name: "{autodesktop}\Min's Modding & Mapping Utility"; Filename: "{app}\MinModdingMappingUtility.exe"; WorkingDir: "{app}"; Tasks: desktopicon

    [Run]
    Filename: "{app}\MinModdingMappingUtility.exe"; WorkingDir: "{app}"; Description: "Launch Min's Modding & Mapping Utility"; Flags: postinstall nowait skipifsilent