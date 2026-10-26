param([string]$Channel='stable')
$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'
$Root=Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Version=(& python -c 'from app_info import VERSION; print(VERSION)').Trim()
if ($Channel -notin @('stable','preview')) { throw 'Unknown channel' }
$Dist=Join-Path $Root 'release-dist'
$Work=Join-Path $Root 'release-build'
$Stage=Join-Path $Work 'windows-stage'
New-Item -Force -ItemType Directory $Dist,$Work | Out-Null
if(Test-Path $Stage){Remove-Item -Recurse -Force $Stage}
New-Item -ItemType Directory $Stage | Out-Null
& python -m PyInstaller --noconfirm --clean --onedir --name study-backend --distpath "$Work/backend-dist" --workpath "$Work/pyinstaller" --specpath $Work --add-data "$Root/static;static" --collect-data certifi --collect-data tzdata --hidden-import tzdata --hidden-import pypdf "$Root/backend_entry.py"
if($LASTEXITCODE -ne 0){throw 'PyInstaller failed'}
Copy-Item -Recurse "$Work/backend-dist/study-backend" "$Stage/backend"
$SdkVersion='1.0.4314.35'
$Package=Join-Path $Work 'webview2.zip'
Invoke-WebRequest "https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/$SdkVersion/microsoft.web.webview2.$SdkVersion.nupkg" -OutFile $Package
if((Get-FileHash $Package -Algorithm SHA256).Hash.ToLower() -ne '90778deb1b77e36292828b4b5833c9255c27533f40e0ddd55891ae718944edc4'){throw 'WebView2 SDK checksum mismatch'}
$Sdk=Join-Path $Work 'webview2-sdk'
Expand-Archive -Path $Package -DestinationPath $Sdk -Force
$Preview=if($Channel -eq 'preview'){'ON'}else{'OFF'}
& cmake -S native/windows -B "$Work/windows-native" -A x64 "-DWEBVIEW2_SDK=$Sdk" "-DSTUDY_PREVIEW=$Preview"
if($LASTEXITCODE -ne 0){throw 'CMake configure failed'}
& cmake --build "$Work/windows-native" --config Release
if($LASTEXITCODE -ne 0){throw 'Native build failed'}
Copy-Item "$Work/windows-native/Release/DailyStudy.exe" $Stage
Copy-Item docs/usage.md "$Stage/README.md"
$Licenses=Join-Path $Stage 'ThirdPartyLicenses'
New-Item -ItemType Directory -Force $Licenses | Out-Null
Copy-Item "$Sdk/LICENSE.txt" "$Licenses/WebView2-LICENSE.txt"
Copy-Item static/vendor/*LICENSE* $Licenses
& python tools/runtime_licenses.py $Licenses
if($LASTEXITCODE -ne 0){throw 'License collection failed'}
$Base="DailyStudy-$Version-windows-x64"
if($Channel -eq 'preview'){$Base+="-preview"}
Compress-Archive -Path "$Stage/*" -DestinationPath "$Dist/$Base.zip" -Force
$Iscc="${env:ProgramFiles(x86)}/Inno Setup 6/ISCC.exe"
if(!(Test-Path $Iscc)){
 & choco install innosetup --yes --no-progress
 if($LASTEXITCODE -ne 0){throw 'Inno Setup install failed'}
}
$Name=if($Channel -eq 'preview'){'Daily Study Preview'}else{'Daily Study'}
$AppId=if($Channel -eq 'preview'){'F6C530BA-438B-4127-A038-FF76DF3D1972'}else{'C138DD14-C4F3-46F6-9657-2358AC7E3C54'}
$Iss=@"
[Setup]
AppId={{$AppId}
AppName=$Name
AppVersion=$Version
AppPublisher=frostloom
AppPublisherURL=https://github.com/frostloom/study
AppUpdatesURL=https://github.com/frostloom/study/releases
DefaultDirName={localappdata}\Programs\$Name
DefaultGroupName=$Name
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=$Dist
OutputBaseFilename=$Base-setup
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\DailyStudy.exe
[Files]
Source: "$Stage\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\$Name"; Filename: "{app}\DailyStudy.exe"
[Run]
Filename: "{app}\DailyStudy.exe"; Description: "Open $Name"; Flags: nowait postinstall skipifsilent
"@
$IssFile=Join-Path $Work 'DailyStudy.iss'
[IO.File]::WriteAllText($IssFile,$Iss,[Text.UTF8Encoding]::new($true))
& $Iscc $IssFile
if($LASTEXITCODE -ne 0){throw 'Installer build failed'}
Get-ChildItem $Dist -File | Where-Object {$_.Extension -in '.zip','.exe'} | ForEach-Object {"$((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower())  $($_.Name)"} | Set-Content -Encoding utf8 "$Dist/SHA256SUMS-windows.txt"
