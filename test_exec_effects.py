# -*- coding: utf-8 -*-
"""
Wirkungstests fuer Dateimeister_exec.MyExecWindow.exec_handler.

Waehrend test_exec.py nur prueft, DASS subprocess.Popen mit dem
richtigen Kommando aufgerufen wird (Stub), pruefen diese Tests,
WAS das Kommando tatsaechlich tut: kopiert es die richtigen Dateien,
loescht es die richtigen Dateien, laeuft delrelpath nur im
delete-Fall?

Quelle:  regtest-images/jpeg/ (rekursiv, alle Dateien und Unterordner)
Ziel:    sandbox.images/dst/ (Sandbox, wird nach dem Test weggeworfen)

regtest-images/ wird nur gelesen, nie beschrieben.

Voraussetzung: Windows (die Skripte sind .cmd-Dateien und werden via
cmd.exe / call ausgefuehrt). Auf Linux/macOS werden die Tests
uebersprungen.
"""

import os
import sys

import pytest

import Dateimeister_exec as DE


pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="exec_handler runs .cmd scripts via cmd.exe"
)


# ----------------------------------------------------------------------
# Quellverzeichnis: regtest-images/jpeg/ (rekursiv)
# ----------------------------------------------------------------------
REGTEST_DIR   = os.path.dirname(os.path.abspath(__file__))
TESTDATEN_DIR = os.path.dirname(REGTEST_DIR)
SOURCE_ROOT   = os.path.join(TESTDATEN_DIR, "regtest", "regtest-images", "jpeg")


def _collect_source_files(root):
    """Alle Dateien unter root, rekursiv, als absolute Pfade."""
    result = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            result.append(os.path.join(dirpath, name))
    return sorted(result)


def _rel_to(root, path):
    """Relativer Pfad von path unter root, mit '/' als Trenner."""
    return os.path.relpath(path, root).replace("\\", "/")


# ----------------------------------------------------------------------
# Fixture: echte Bilder in der Sandbox
# ----------------------------------------------------------------------
@pytest.fixture
def exec_sandbox(sandbox):
    """Baut eine Sandbox mit allen Dateien aus regtest-images/jpeg/.

    Struktur:
        sandbox.images/dst/<relpath>        Ziel-Dateien (zunaechst leer)
        sandbox.datadir/daten/cmd/_copy.cmd          kopiert alle Quelldateien
        sandbox.datadir/daten/cmd/_delete.cmd        loescht alle Zieldateien
        sandbox.datadir/daten/cmd/_delrelpath.cmd    entfernt einen Unterordner

    Die .cmd-Skripte spiegeln die Struktur der echten Dateien: fuer jede
    Quelldatei in regtest-images/jpeg/<relpath> wird im Ziel
    sandbox.images/dst/<relpath> angelegt.
    """
    if not os.path.isdir(SOURCE_ROOT):
        pytest.skip("Regtest-Images fehlen: %s" % SOURCE_ROOT)

    src_files = _collect_source_files(SOURCE_ROOT)
    if not src_files:
        pytest.skip("Keine Quelldateien unter %s" % SOURCE_ROOT)

    dst_dir = os.path.join(sandbox.images, "dst")
    os.makedirs(dst_dir, exist_ok=True)

    # Ein Unterordner im Ziel, den delrelpath spaeter entfernen soll.
    # Wir nehmen den ersten Unterordner aus der Quellstruktur, damit
    # die Namen realistisch sind (z.B. 'aa', 'aa/bb', 'bearbeitet').
    sub_dirs_in_src = set()
    for src in src_files:
        rel = _rel_to(SOURCE_ROOT, src)
        parts = rel.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            sub_dirs_in_src.add("/".join(parts[:i]))
    # Sortiert nach Tiefe absteigend, damit wir den tiefsten nehmen
    sub_dirs_sorted = sorted(sub_dirs_in_src,
                             key=lambda p: p.count("/"), reverse=True)
    if sub_dirs_sorted:
        dst_sub_rel = sub_dirs_sorted[0]
    else:
        dst_sub_rel = "sub"  # Fallback, falls die Quelle keine Unterordner hat
    dst_sub = os.path.join(dst_dir, *dst_sub_rel.split("/"))
    os.makedirs(dst_sub, exist_ok=True)
    # Eine Marker-Datei, damit der Ordner nicht leer ist (Windows-
    # rmdir /S /Q loescht auch leere Ordner, aber ein Test der pruefen
    # will, dass delrelpath etwas entfernt, sollte das an einer
    # konkreten Datei festmachen koennen).
    sub_marker = os.path.join(dst_sub, "_delrelpath_marker.txt")
    with open(sub_marker, "w", encoding="utf-8") as f:
        f.write("delrelpath marker\n")

    # cmd-Verzeichnis
    cmd_dir = os.path.join(sandbox.datadir, "daten", "cmd")
    os.makedirs(cmd_dir, exist_ok=True)

    # --- Copy-Skript: kopiert ALLE Quelldateien ins Ziel (mit relpath) ---
    copy_lines = ["@echo off"]
    for src in src_files:
        rel = _rel_to(SOURCE_ROOT, src)
        target = os.path.join(dst_dir, *rel.split("/"))
        # Ziel-Unterordner sicherstellen
        target_parent = os.path.dirname(target)
        copy_lines.append(f'mkdir "{target_parent}" 2>nul')
        copy_lines.append(f'copy /Y "{src}" "{target}"')
    copy_path = os.path.join(cmd_dir, "_copy.cmd")
    with open(copy_path, "w", encoding="latin-1") as f:
        f.write("\r\n".join(copy_lines) + "\r\n")

    # --- Delete-Skript: loescht ALLE Zieldateien ---
    del_lines = ["@echo off"]
    for src in src_files:
        rel = _rel_to(SOURCE_ROOT, src)
        target = os.path.join(dst_dir, *rel.split("/"))
        del_lines.append(f'del /Q "{target}"')
    delete_path = os.path.join(cmd_dir, "_delete.cmd")
    with open(delete_path, "w", encoding="latin-1") as f:
        f.write("\r\n".join(del_lines) + "\r\n")

    # --- Delrelpath-Skript: entfernt den gewaehlten Unterordner ---
    delrel_lines = [
        "@echo off",
        f'rmdir /S /Q "{dst_sub}"',
    ]
    delrelpath_path = os.path.join(cmd_dir, "_delrelpath.cmd")
    with open(delrelpath_path, "w", encoding="latin-1") as f:
        f.write("\r\n".join(delrel_lines) + "\r\n")

    win = DE.MyExecWindow(
        pmain=None,
        datadir=sandbox.datadir,
        cmd_files_subdir="daten/cmd",
        imagetype="JPEG",
        copyscript=copy_path,
        deletescript=delete_path,
        delrelpathscript=delrelpath_path,
    )
    try:
        yield {
            "win": win,
            "src_root": SOURCE_ROOT,
            "src_files": src_files,
            "dst_dir": dst_dir,
            "dst_sub": dst_sub,
            "dst_sub_rel": dst_sub_rel,
            "sub_marker": sub_marker,
        }
    finally:
        try:
            win.close_handler()
        except Exception:
            pass


# ----------------------------------------------------------------------
# Copy
# ----------------------------------------------------------------------
def test_copy_actually_copies_files(exec_sandbox):
    """Copy-Skript laeuft durch; im Ziel existiert jede Quelldatei unter
    demselben relativen Pfad, mit identischem Inhalt."""
    win = exec_sandbox["win"]
    src_root = exec_sandbox["src_root"]
    src_files = exec_sandbox["src_files"]
    dst_dir = exec_sandbox["dst_dir"]

    # Vor dem Lauf: Ziel-Dateien fehlen
    for src in src_files:
        rel = _rel_to(src_root, src)
        dst = os.path.join(dst_dir, *rel.split("/"))
        assert not os.path.exists(dst), (
            "Zieldatei existiert bereits vor dem Copy: %s" % dst)

    win.rb_value.set("copy")
    win.script_select()
    win.exec_handler()

    # Nach dem Lauf: Ziel-Dateien existieren und sind inhaltsgleich
    n_ok = 0
    for src in src_files:
        rel = _rel_to(src_root, src)
        dst = os.path.join(dst_dir, *rel.split("/"))
        assert os.path.isfile(dst), "Zieldatei fehlt: %s" % dst
        with open(src, "rb") as f:
            src_bytes = f.read()
        with open(dst, "rb") as f:
            dst_bytes = f.read()
        assert src_bytes == dst_bytes, (
            "Inhalt weicht ab fuer %s" % rel)
        n_ok += 1
    # Sicherheitsnetz: mindestens eine Datei muss geprueft worden sein
    assert n_ok > 0


def test_copy_writes_output_to_messages_field(exec_sandbox):
    """Nach dem Copy-Lauf steht die Ausgabe des cmd-Skripts im
    Messages-Feld (copy /Y schreibt '1 file(s) copied.' o.ae.)."""
    win = exec_sandbox["win"]
    win.rb_value.set("copy")
    win.script_select()
    win.exec_handler()

    msgs = win.Text_messages.get("1.0", "end-1c")
    # cmd.exe schreibt bei copy eine Bestaetigung; genauer Wortlaut
    # haengt von der Sprache ab, deshalb nur pruefen, dass ueberhaupt
    # etwas drinsteht.
    assert msgs.strip() != ""


# ----------------------------------------------------------------------
# Delete ohne delrelpath
# ----------------------------------------------------------------------
def test_delete_removes_files_without_touching_subdir(exec_sandbox):
    """Delete-Skript loescht die Zieldateien, aber der Unterordner
    'sub' (bzw. der tiefste Quell-Unterordner) bleibt bestehen
    (delrelpath ist aus)."""
    win = exec_sandbox["win"]
    src_root = exec_sandbox["src_root"]
    src_files = exec_sandbox["src_files"]
    dst_dir = exec_sandbox["dst_dir"]
    dst_sub = exec_sandbox["dst_sub"]

    # Vorbedingung: Zieldateien existieren
    for src in src_files:
        rel = _rel_to(src_root, src)
        dst = os.path.join(dst_dir, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(b"x")
    assert os.path.isdir(dst_sub)

    win.rb_value.set("delete")
    win.script_select()
    win.cb_delrelpath_var.set(0)   # delrelpath AUS
    win.exec_handler()

    # Zieldateien weg
    for src in src_files:
        rel = _rel_to(src_root, src)
        dst = os.path.join(dst_dir, *rel.split("/"))
        assert not os.path.exists(dst), "Zieldatei nicht geloescht: %s" % dst
    # Unterordner noch da
    assert os.path.isdir(dst_sub), (
        "delrelpath war aus, aber der Unterordner %s wurde entfernt" % dst_sub)


# ----------------------------------------------------------------------
# Delete mit delrelpath
# ----------------------------------------------------------------------
def test_delete_with_delrelpath_also_removes_subdir(exec_sandbox):
    """Delete + delrelpath: Zieldateien weg UND der Unterordner
    'sub' (bzw. der tiefste Quell-Unterordner) wird entfernt."""
    win = exec_sandbox["win"]
    src_root = exec_sandbox["src_root"]
    src_files = exec_sandbox["src_files"]
    dst_dir = exec_sandbox["dst_dir"]
    dst_sub = exec_sandbox["dst_sub"]

    for src in src_files:
        rel = _rel_to(src_root, src)
        dst = os.path.join(dst_dir, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(b"x")
    assert os.path.isdir(dst_sub)

    win.rb_value.set("delete")
    win.script_select()
    win.cb_delrelpath_var.set(1)   # delrelpath AN
    win.exec_handler()

    for src in src_files:
        rel = _rel_to(src_root, src)
        dst = os.path.join(dst_dir, *rel.split("/"))
        assert not os.path.exists(dst), "Zieldatei nicht geloescht: %s" % dst
    assert not os.path.isdir(dst_sub), (
        "delrelpath war an, aber der Unterordner %s existiert noch" % dst_sub)


# ----------------------------------------------------------------------
# Copy ignoriert delrelpath-Flag
# ----------------------------------------------------------------------
def test_copy_ignores_delrelpath_flag(exec_sandbox):
    """delrelpath-Flag gesetzt, aber action == 'copy': Unterordner
    bleibt unangetastet (delrelpath laeuft nur bei delete)."""
    win = exec_sandbox["win"]
    src_root = exec_sandbox["src_root"]
    src_files = exec_sandbox["src_files"]
    dst_dir = exec_sandbox["dst_dir"]
    dst_sub = exec_sandbox["dst_sub"]

    # Vorbedingung: Zieldateien existieren
    for src in src_files:
        rel = _rel_to(src_root, src)
        dst = os.path.join(dst_dir, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(b"x")
    assert os.path.isdir(dst_sub)

    win.rb_value.set("copy")
    win.script_select()
    win.cb_delrelpath_var.set(1)   # Flag gesetzt, darf aber nichts tun
    win.exec_handler()

    # Copy hat die Dateien ueberschrieben (sie existieren weiterhin)
    for src in src_files:
        rel = _rel_to(src_root, src)
        dst = os.path.join(dst_dir, *rel.split("/"))
        assert os.path.isfile(dst), "Zieldatei fehlt nach Copy: %s" % dst
    # Unterordner unangetastet
    assert os.path.isdir(dst_sub), (
        "delrelpath-Flag wurde bei action == 'copy' ausgewertet")