@echo off
REM ----------------------------------------------------------------------
REM run_regtest.cmd - fuehrt die Regressionstests aus und schreibt pro
REM Lauf eine eigene Log-Datei nach artifacts\logs\.
REM
REM Verwendung:
REM     run_regtest.cmd
REM     run_regtest.cmd test_camera_dialog.py
REM     run_regtest.cmd test_fsimage.py test_fsvideo.py
REM
REM Ohne Argumente werden alle test_*.py im aktuellen Verzeichnis gelaufen.
REM
REM Hinweis: Die Ausgabe auf der Konsole ist weiss (keine Farben), weil
REM die Umleitung ueber eine temporaere Datei geht. Fuer farbige Ausgabe
REM gibt es run_regtest_console.cmd.
REM
REM Exitcode von pytest wird als Exitcode des Skripts weitergegeben.
REM ----------------------------------------------------------------------

setlocal enabledelayedexpansion

set "REGTEST_DIR=%~dp0"
cd /d "%REGTEST_DIR%"

REM Zeitstempel bauen (YYYYMMDD_HHMMSS) aus %date% und %time%
REM Beispiel DE: date=06.10.2026, time=18:15:23,45
set "DD=%date:~0,2%"
set "MM=%date:~3,2%"
set "YYYY=%date:~6,4%"
set "HH=%time:~0,2%"
set "MIN=%time:~3,2%"
set "SEC=%time:~6,2%"
REM Fuehrende Leerzeichen durch 0 ersetzen (passiert bei Stunden < 10)
set "HH=%HH: =0%"
set "STAMP=%YYYY%%MM%%DD%_%HH%%MIN%%SEC%"

set "LOGDIR=%REGTEST_DIR%artifacts\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set "LOGFILE=%LOGDIR%\regtest_%STAMP%.log"

REM Kopf in die Logdatei schreiben
echo ================================================== >  "%LOGFILE%"
echo Dateimeister Regressionstest                       >> "%LOGFILE%"
echo Start:  %date% %time%                              >> "%LOGFILE%"
echo Rechner: %COMPUTERNAME%                             >> "%LOGFILE%"
echo ================================================== >> "%LOGFILE%"
echo. >> "%LOGFILE%"

REM Tests sammeln
if "%~1"=="" (
    set "TESTLIST="
    for %%F in (test_*.py) do (
        set "TESTLIST=!TESTLIST! %%F"
    )
    if "!TESTLIST!"=="" (
        echo FEHLER: Keine test_*.py im Verzeichnis %REGTEST_DIR% gefunden.
        endlocal
        exit /b 1
    )
) else (
    set "TESTLIST=%*"
)
echo Tests:!TESTLIST! >> "%LOGFILE%"
echo. >> "%LOGFILE%"

REM Header auf der Konsole
echo ==================================================
echo Dateimeister Regressionstest
echo Start:  %date% %time%
echo Tests: !TESTLIST!
echo Log:    %LOGFILE%
echo ==================================================
echo.

REM pytest laufen lassen. Ausgabe in die Logdatei umleiten.
python -m pytest !TESTLIST! -v >> "%LOGFILE%" 2>&1
set "RC=%errorlevel%"

REM Schlusszeile ins Log
echo. >> "%LOGFILE%"
echo ================================================== >> "%LOGFILE%"
echo Ende:   %date% %time%   Exitcode: %RC% >> "%LOGFILE%"
echo ================================================== >> "%LOGFILE%"

REM Fertig-Meldung auf der Konsole
echo.
echo ==================================================
if "%RC%"=="0" (
    echo Fertig. Alle Tests bestanden.
) else (
    echo Fertig. Es gab Fehler. Exitcode: %RC%
)
echo Log: %LOGFILE%
echo ==================================================

endlocal & exit /b %RC%