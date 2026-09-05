param(
    [int]$Minutes = 15,
    [string]$TaskName = "SCGameTracker"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $Execute = $VenvPython
    $Argument = "-m src.sync"
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCmd) {
        throw "Python was not found. Create .venv first."
    }
    $Execute = $PythonCmd.Source
    $Argument = "`"$Root\sync.py`""
}

$Action = New-ScheduledTaskAction -Execute $Execute -Argument $Argument -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $Minutes)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
Write-Host "Scheduled task '$TaskName' will run every $Minutes minutes."
Write-Host "Working directory: $Root"
Write-Host "Command: $Execute $Argument"
