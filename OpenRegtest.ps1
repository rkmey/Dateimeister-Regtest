param(
    [string]$TargetDir
)

# ---------------------------------------------------------------
# Error handling: on any error, print the message and wait for
# Enter, so the console window does not close before the user
# can read what went wrong. On success, the script finishes
# normally and the console closes by itself (no -NoExit in the
# shortcut).
# ---------------------------------------------------------------
$ErrorActionPreference = "Stop"

trap {
    Write-Host ""
    Write-Host "FEHLER:" -ForegroundColor Red
    Write-Host $_
    Write-Host ""
    Write-Host "Druecke Enter, um das Fenster zu schliessen..."
    Read-Host
    exit 1
}

# If no directory was passed, use the directory of the script.
if (-not $TargetDir) {
    $TargetDir = $PSScriptRoot
}

if (-not (Test-Path $TargetDir)) {
    Write-Error "Das angegebene Verzeichnis '$TargetDir' existiert nicht."
    exit 1
}

Write-Host "Regtest-Umgebung wird gestartet in:"
Write-Host "  $TargetDir"
Write-Host ""

# Open Explorer in the regtest directory
Start-Process explorer.exe $TargetDir

# Open Git Bash in the regtest directory
Start-Process "C:\Program Files\Git\git-bash.exe" --cd="$TargetDir"

# Open the cmd window via startcmd.bat (classic console with
# the saved window properties, independent of Windows Terminal)
Start-Process -FilePath "$TargetDir\startcmd.bat" -WorkingDirectory $TargetDir

Write-Host "Fertig."