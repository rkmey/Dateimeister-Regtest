param(
    [string]$TargetDir
)

# Falls kein Verzeichnis uebergeben wurde, das Verzeichnis des Skripts nehmen
if (-not $TargetDir) {
    $TargetDir = $PSScriptRoot
}

if (-not (Test-Path $TargetDir)) {
    Write-Error "Das angegebene Verzeichnis '$TargetDir' existiert nicht."
    exit 1
}

# Explorer im regtest-Verzeichnis oeffnen
Start-Process explorer.exe $TargetDir

# Git Bash im regtest-Verzeichnis oeffnen
Start-Process "C:\Program Files\Git\git-bash.exe" --cd="$TargetDir"

# cmd-Fenster ueber startcmd.bat oeffnen
Start-Process -FilePath "$TargetDir\startcmd.bat" -WorkingDirectory $TargetDir