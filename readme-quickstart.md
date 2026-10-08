Regressionstests fuer Dateimeister.
---------------------------------

Inhalt:
    conftest.py              pytest-Fixtures (siehe Chat)
    test_camera_dialog.py    Testfall Kamera-Dialog
    test_fsimage.py          (spaeter) MyFSImage-Tests
    test_print_preview.py    (spaeter) PrintPreview-Tests
    test_events.py           (spaeter) EventManager-Tests

Starten (Windows):
    cd regtest
    pytest -v

Starten (Linux):
    cd regtest
    xvfb-run -a pytest -v

Das Programmverzeichnis wird ueber die Umgebungsvariable
DATEIMEISTER_HOME gesetzt. Standard ist:
    <Dateimeister-Testdaten>/../Dateimeister

Beispiel (Windows cmd):
    set DATEIMEISTER_HOME=C:\Arbeit\python\Dateimeister
    pytest -v
