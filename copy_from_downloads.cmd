@echo off
REM ----------------------------------------------------------------------
REM copy_from_downloads.cmd
REM
REM Kopiert die neueste deepseek_python_*.py aus dem Download-Ordner
REM ins aktuelle Verzeichnis unter einem von dir angegebenen Namen.
REM
REM Verwendung:
REM     copy_from_downloads.cmd conftest.py
REM     copy_from_downloads.cmd test_camera_dialog.py
REM     copy_from_downloads.cmd tools.py
REM
REM Optional: Alter in Sekunden, um nur sehr frische Downloads zu nehmen.
REM           Standard 3600 (1 Stunde).
REM ----------------------------------------------------------------------

setlocal enabledelayedexpansion

REM Download-Ordner
set "DOWNLOADS=%USERPROFILE%\Downloads"
if not exist "%DOWNLOADS%" (
    echo FEHLER: Download-Ordner nicht gefunden: %DOWNLOADS%
    exit /b 1
)

REM Zielname
if "%~1"=="" (
    echo Verwendung: %~nx0 ^<zielname^>
    echo Beispiel:   %~nx0 conftest.py
    exit /b 1
)
set "TARGET=%~1"

REM Neueste deepseek_python_*.py im Download-Ordner suchen
echo Suche neueste deepseek_python_*.py in %DOWNLOADS% ...
set "SRC="
for /f "delims=" %%F in ('dir /b /a-d /o-d "%DOWNLOADS%\deepseek_python_*.py" 2^>nul') do (
    if not defined SRC set "SRC=%DOWNLOADS%\%%F"
)

if not defined SRC (
    echo FEHLER: Keine deepseek_python_*.py in %DOWNLOADS% gefunden.
    exit /b 1
)
echo Quelle:    %SRC%

REM Zielverzeichnis = aktuelles Verzeichnis
set "DST=%~dp0%TARGET%"
echo Ziel:      %DST%

if /i "%SRC%"=="%DST%" (
    echo Quelle und Ziel sind identisch - nichts zu tun.
    exit /b 0
)

REM Kopieren
copy /Y "%SRC%" "%DST%" >nul
if errorlevel 1 (
    echo FEHLER beim Kopieren.
    exit /b 1
)

echo Fertig. %TARGET% wurde aktualisiert.
endlocal
exit /b 0