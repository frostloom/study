param([ValidateSet('build','smoke')][string]$Task)
$ErrorActionPreference='Stop'
try {
 if($Task -eq 'build'){ & "$PSScriptRoot/build_windows.ps1" }
 else { & "$PSScriptRoot/windows-smoke.ps1" }
} catch {
 $Text=($_ | Out-String) + "`n" + $_.ScriptStackTrace
 $Text=$Text.Replace('%','%25').Replace("`r",'%0D').Replace("`n",'%0A')
 Write-Output "::error title=Windows $Task diagnostics::$Text"
 $Log=Join-Path $env:RUNNER_TEMP 'study-native-smoke/native-backend.log'
 if(Test-Path $Log){$Tail=((Get-Content -Tail 30 -Encoding UTF8 $Log) -join '%0A').Replace('%','%25');Write-Output "::error title=Native backend diagnostics::$Tail"}
 exit 1
}
exit 0
