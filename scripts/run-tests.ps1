$ErrorActionPreference = "Stop"
$logFile = "$PSScriptRoot/test-build.log"
$timeoutSeconds = 180

$proc = Start-Process -FilePath "mvn" -ArgumentList "verify" -WorkingDirectory "$PSScriptRoot\.." -NoNewWindow -PassThru -RedirectStandardOutput $logFile -RedirectStandardError "$logFile.err"

$deadline = (Get-Date).AddSeconds($timeoutSeconds)
while (!$proc.HasExited -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
}

if (!$proc.HasExited) {
    $proc.Kill()
    Write-Host "BUILD TIMED OUT after $timeoutSeconds seconds"
    Get-Content $logFile -Tail 30
    exit 1
}

Get-Content $logFile -Tail 40

if ($proc.ExitCode -eq 0) {
    $totalTests = Select-String -Path $logFile -Pattern "Tests run: (\d+)" | ForEach-Object {
        if ($_.Line -match "Tests run: (\d+)") { [int]$Matches[1] }
    } | Measure-Object -Sum | ForEach-Object { $_.Sum }
    Write-Host "`nBUILD SUCCESS - Total tests: $totalTests"
} else {
    Write-Host "`nBUILD FAILED (exit code $($proc.ExitCode))"
}

exit $proc.ExitCode
