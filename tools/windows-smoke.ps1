$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'
& python tools/smoke_backend.py release-build/windows-stage/backend/study-backend.exe
if($LASTEXITCODE -ne 0){throw 'Frozen backend smoke failed'}
& python -c "from process_limits import windows_pdf_limits; windows_pdf_limits(); bytearray(700*1024*1024)"
if($LASTEXITCODE -eq 0){throw 'PDF worker Windows memory ceiling not enforced'}
$global:LASTEXITCODE=0
$Root=Join-Path $env:RUNNER_TEMP 'study-native-smoke'
$App=Start-Process -FilePath "$PWD/release-build/windows-stage/DailyStudy.exe" -ArgumentList '--data-dir',"`"$Root`"" -PassThru
try {
 $Deadline=(Get-Date).AddSeconds(40)
 do { Start-Sleep -Milliseconds 500; $App.Refresh(); if($App.HasExited){throw 'Native app exited'} } until((Test-Path "$Root/.server-info.json") -or (Get-Date) -gt $Deadline)
 if(!(Test-Path "$Root/.server-info.json")){throw 'Native backend never became ready'}
 $Info=Get-Content -Raw -Encoding UTF8 "$Root/.server-info.json" | ConvertFrom-Json
 $Setup=Invoke-RestMethod "http://127.0.0.1:$($Info.port)/api/setup"
 if($Setup.ready){throw 'Fresh data unexpectedly ready'}
 $Deadline=(Get-Date).AddSeconds(20)
 do { Start-Sleep -Milliseconds 500;$App.Refresh() } until($App.MainWindowHandle -ne 0 -or (Get-Date) -gt $Deadline)
 if($App.MainWindowHandle -eq 0){throw 'No native application window'}
 $Deadline=(Get-Date).AddSeconds(30)
 do { Start-Sleep -Milliseconds 500 } until((Test-Path "$Root/.window-state.json") -or (Get-Date) -gt $Deadline)
 if(!(Test-Path "$Root/.window-state.json")){throw 'WebView2 never rendered the learning UI'}
 Write-Host 'Windows native window and owned backend startup passed'
 $App.CloseMainWindow() | Out-Null
 if(!$App.WaitForExit(10000)){throw 'Native close did not exit'}
 Start-Sleep -Seconds 2
 if(Get-Process -Id $Info.pid -ErrorAction SilentlyContinue){throw 'Owned backend survived window close'}
} finally { if(!$App.HasExited){Stop-Process -Id $App.Id} }
