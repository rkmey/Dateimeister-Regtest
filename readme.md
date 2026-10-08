# Dateimeister Regressionstests

Testumgebung für die Regressionstests des Dateimeister-Projekts.

Stand: 29.09.2026 – Testfall 1 (Kamera-Dialog) abgeschlossen, 19 Tests grün.

---

## 1. Verzeichnisstruktur

```
Dateimeister-Testdaten\                      <- Testdaten-Wurzel
    setup_regtest.py                         <- Einmalig: legt Verzeichnisstruktur an
    regtest\                                 <- Testsuite
        README.md                            <- diese Datei
        pytest.ini                           <- pytest-Konfiguration (Timeouts)
        conftest.py                          <- zentrale Fixtures, Mocks, Pfade
        test_camera_dialog.py                <- Testfall 1: Kamera-Dialog (19 Tests)
        copy_from_downloads.cmd              <- Kopier-Skript für Downloads
        run_regtest.cmd                      <- (optional) Nachtlauf mit Log
        __init__.py                          <- markiert regtest als Paket
        artifacts\                           <- alles, was die Tests erzeugen
            <modulname>\<testname>\
                datadir\
                    daten\config\            <- XML, die der Test schreibt
                    daten\cmd\
                    daten\temp\
                images\
                xml\
                ini\
                logs\

Dateimeister\                                <- Programmverzeichnis (bleibt unberührt)
    Dateimeister_support.py
    tools.py
    dateimeister_config_xml.py
    ...
```

Wichtig: Die Tests schreiben **niemals** ins Programmverzeichnis.
Alles landet unter `regtest\artifacts\`.

---

## 2. Voraussetzungen

```
pip install pytest pytest-timeout
```

`pytest-timeout` ist nötig, damit hängende Tests nach 60 Sekunden
abgebrochen werden und der Nachtlauf nicht blockiert.

Auf Linux zusätzlich `xvfb-run` (wegen Tk ohne Display):

```
sudo apt install xvfb
```

---

## 3. Befehle im Alltag

Alle Befehle werden aus dem Verzeichnis `regtest\` heraus ausgeführt.

### 3.1 Testfall ausführen

```
cd C:\Arbeit\python\Dateimeister-Testdaten\regtest
python -m pytest test_camera_dialog.py -v
```

Erwartete Ausgabe bei Erfolg:

```
19 passed in 2.35s
```

### 3.2 Nur einen einzelnen Test ausführen

```
python -m pytest test_camera_dialog.py::test_apply_new_camera_new -v
```

### 3.3 Tests mit einem Stichwort filtern

```
python -m pytest -k "suffix" -v
```

### 3.4 Tests mit Ausgabe (print) anzeigen

```
python -m pytest test_camera_dialog.py -v -s
```

### 3.5 Abbruch beim ersten Fehler

```
python -m pytest test_camera_dialog.py -v -x
```
### 3.5 Docstring der Testdokumentation auslesen

```
python -m pytest test_fsimage.py --collect-only

---

## 4. Datei aus dem Download-Ordner kopieren

DeepSeek speichert jede Datei unter einem generierten Namen
(`deepseek_python_<datum>_<hash>.py`). Mit `copy_from_downloads.cmd`
wird die neueste Datei aus dem Download-Ordner ins aktuelle
Verzeichnis kopiert, unter dem gewünschten Zielnamen:

```
copy_from_downloads.cmd conftest.py
copy_from_downloads.cmd test_camera_dialog.py
```

Das Skript sucht die neueste `deepseek_python_*.py` in
`%USERPROFILE%\Downloads` und überschreibt eine eventuell vorhandene
Zieldatei im aktuellen Verzeichnis.

Inhalt des Skripts `copy_from_downloads.cmd` (falls du es neu anlegen musst):


## 5. Wo schaue ich nach, wenn ein Test rot ist?

Pro Test wird ein eigener Sandbox-Ordner angelegt. Der Pfad steht
in der pytest-Ausgabe als `tmp_xml = ...`. Beispiel:

```
artifacts\camera_dialog\test_apply_new_type_subdir\
    xml\dateimeister_configfiles.xml
```

Dort steht die XML, wie der Test sie verändert hat. Wenn ein Test
rot ist, ist das oft die erste Adresse, um zu verstehen, was
schiefgelaufen ist.

Zur Info: `artifacts\` wird **nicht** automatisch geleert, damit du
nach einem roten Lauf die Spuren inspizieren kannst. Beim erneuten
Lauf desselben Tests wird nur der jeweilige `<testname>`-Ordner
geleert.

---

## 6. Nachtlauf

Für den unbeaufsichtigten Lauf empfehlen sich diese Optionen:

```
python -m pytest regtest\ -v --timeout=60 --timeout-method=thread
```

Was dabei passiert:

- **60 Sekunden pro Test** – hängende Tests werden abgebrochen, der
  Lauf geht weiter.
- **30 Minuten pro Session** – Notbremse, falls mehrere Tests
  hintereinander hängen.
- **Keine Messageboxen** – `conftest.py` mockt `tkinter.messagebox`
  und `tools.info_box` automatisch für alle Tests. Es kann keine
  echte Dialogbox mehr auftauchen und den Lauf blockieren.
- **Kontextmenüs werden nicht angezeigt** – `retrieve_item` befüllt
  das Menü, aber `self.event` ist `None`, sodass `context_menu.post`
  nicht aufgerufen wird.
- **Offene Fenster werden gemeldet** – nach jedem Test prüft ein
  Hook in `conftest.py`, ob noch Toplevel-Fenster offen sind, und
  loggt Testname + Fenstertitel als Warnung.

Für einen Windows-Aufgabenplaner-Task z. B. um 2:00 Uhr nachts:

```
cd C:\Arbeit\python\Dateimeister-Testdaten\regtest
python -m pytest -v > artifacts\logs\nightly_%date%.log 2>&1
```

---

## 7. Testsuiten und was sie prüfen

### 7.1 test_camera_dialog.py – Kamera-Dialog (`MyCameraTreeview`)

19 Tests, aufgeteilt in 5 Gruppen:

**1. Baum-Aufbau (2 Tests)**
- `test_treeview_from_xml_builds_hierarchy`
- `test_treeview_from_xml_prompts_for_missing_process_image`

**2. Kamera-Aktionen (3 Tests)**
- `test_apply_new_camera_new`
- `test_apply_new_camera_rename`
- `test_apply_new_camera_delete`

**3. Type-Aktionen (5 Tests)**
- `test_apply_new_type_new`
- `test_apply_new_type_rename`
- `test_apply_new_type_delete`
- `test_apply_new_type_subdir`
- `test_apply_new_type_rendertype`

**4. Suffix-Aktionen (4 Tests)**
- `test_apply_new_suffix_new`
- `test_apply_new_suffix_rename`
- `test_apply_new_suffix_delete`
- `test_apply_new_process_image`

**5. Dialog-Zustand und Kontextmenü (5 Tests)**
- `test_cancel_new_resets_dialog_state`
- `test_context_menu_on_camera_node`
- `test_context_menu_on_type_node`
- `test_context_menu_on_suffix_node`
- `test_apply_new_calls_historize`

Nicht abgedeckt (bewusste Lücken):
- Echte Maus-Klicks im Treeview
- Anzeige des Kontextmenüs (nur Befüllung wird geprüft)
- Undo/Redo-Wirkung (nur Aufruf von `historize_process` geprüft)
- Alle vier Forced-Dialog-Varianten (nur `process_image` geprüft)
- Fehlerfälle (leerer Name, doppelter Name, nicht gefundener Knoten)

---

## 8. Gefundene Bugs

Beim Aufbau dieser Suite gefunden und behoben:

1. **`enable_processing` in `Dateimeister_support.py`**:
   Das `subdir`-Feld wurde beim Vorbelegen ignoriert, wenn im XML
   noch kein Wert stand. Jetzt verhält es sich wie `rendertype` und
   `process_image`.

---

## 9. Grundregeln für neue Tests

1. **Kein `messagebox` im Test.** Falls doch nötig: über
   `silence_messageboxes`-Fixture.
2. **Keine echten mpv-Prozesse.** `MyFSVideo` wird gemockt.
3. **Keine echten Bilder öffnen.** Testbilder werden per PIL
   erzeugt (`Image.new`).
4. **Kein Schreiben außerhalb der Sandbox.** Alle Pfade kommen aus
   dem `sandbox`-Fixture.
5. **Timeout ernst nehmen.** Ein Test, der länger als 60 s braucht,
   ist meistens ein Zeichen für einen blockierten Dialog oder eine
   Endlosschleife – nicht für einen langsamen Test.
6. **Bei neuem Modul:** eigene Testdatei `test_<modul>.py` und
   ggf. neue Fixtures in `conftest.py`.

---

## 10. Fixtures in conftest.py (Übersicht)

Kurzbeschreibung der wichtigsten Fixtures, damit du beim Schreiben
neuer Tests weißt, was schon da ist:

| Fixture | Zweck |
|---|---|
| `tk_root` | Einmaliger Tk-Interpreter (Session-Scope). |
| `sandbox` | Frischer Ordner unter `artifacts\<modul>\<test>` für den Test. |
| `tmp_xml` | Vollständige Test-XML mit Kamera `DIATISCH` (eine Kamera, alles gesetzt). |
| `tmp_xml_incomplete` | XML mit `TESTCAM`, bei der `process_image` fehlt (für Forced Dialog). |
| `empty_xml` | XML ohne Kameras (für Fehlerpfade). |
| `globals_event_manager` | Setzt `Globals.eventManager` auf frischen `EventManager`. |
| `globals_screen` | Setzt `Globals.screen_width/height` auf plausible Werte. |
| `globals_datadir` | Setzt `Globals.datadir` + Subdirs auf die Sandbox. |
| `dummy_main` | Minimaler Ersatz für `Dateimeister_support` als `pmain` für `MyCameraTreeview`. |
| `fake_ur` | Ersetzt `UR.Undo_Redo_Camera` durch einen Fake mit `processid_incr = 10`. |
| `silence_messageboxes` | Zugriff auf gesammelte Messagebox-Aufrufe (autouse-Mock). |
| `silence_tooltips` | Ersetzt `ToolTip` durch einen No-Op-Stub. |

Zusätzlich autouse (ohne dass ein Test sie anfordern muss):

- **Messagebox-Mock**: `showinfo/showwarning/showerror` werden global ersetzt.
- **`tools.info_box`-Mock**: verhindert `sys.exit()` bei `level="fehler"`.
- **Artefakt-Ordner anlegen**: Session-Scope.
- **Window-Cleanup-Hook**: prüft nach jedem Test auf offene Toplevel-Fenster.

---

## 11. Was morgen kommt

**Testfall 2: `MyFSImage` in `Dateimeister_FSimage.py`.**

Relevante Event-Pfade:

- `print_handler()` → feuert `PrintRequestEvent`.
- `on_button_state()` → feuert `FileStateEvent`.
- `close_handler()` → feuert `ClosingEvent`.
- `on_file_state_changed(event)` → reagiert nur, wenn `event.filename == self.file`.
- `on_closing(event)` → schließt nur, wenn `event.obj is self.caller`.

Für den Test brauchen wir ein kleines Bild, das `conftest.py` per
`PIL.Image.new(...)` erzeugt und in der Sandbox speichert.

---

## 12. Kontakt

Diese Suite wird schrittweise erweitert. Bei Fragen zur Struktur
oder zu einzelnen Tests: die Docstrings der Testfunktionen sind
die erste Anlaufstelle, `conftest.py` die zweite.