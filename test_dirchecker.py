# -*- coding: utf-8 -*-
"""
test_dirchecker.py - Regressionstests fuer die schnelle, nicht blockierende
Verzeichnispruefung in tools.py:

    _unc_host, host_reachable, isdir_fast, isfile_fast, true_case_path
    DirChecker (check_bg, check_list, check_on_select, select_in_listbox, mark)

Was abgesichert wird (die Fehler, die wir tatsaechlich hatten):
    * die GUI blockiert nicht, auch wenn die Pruefung lange dauert
    * ein toter Eintrag wird ausgegraut, der erste existierende Eintrag landet im Label
    * Klick auf einen bekannt toten Eintrag: SOFORT Meldung, kein Warten auf den Timeout
    * Klick auf einen noch unbekannten toten Eintrag: Auswahl wird nachtraeglich aufgehoben
    * eine laufende Pruefung wird wiederverwendet (kein neuer Timeout pro Klick)
    * Ergebnis fuer ein inzwischen zerstoertes Widget ist harmlos

Die Tests nutzen echte Tk-Widgets (tk_root aus conftest.py). Netzwerk und Zeit werden
ueber monkeypatch simuliert - es wird nie ein echtes Netzlaufwerk gebraucht.
Fuer Linux: xvfb-run pytest
"""

import os
import sys
import time
import types
import tkinter as tk

import pytest

# Faengt Exceptions in after()-Callbacks fuer ALLE Tests dieses Moduls ab (Fixture aus conftest.py)
pytestmark = pytest.mark.usefixtures("tk_errors")


# ----------------------------------------------------------------------
# Hilfen (pump, tk_frame, dirchk und tk_errors kommen aus conftest.py)
# ----------------------------------------------------------------------
def color(lb, index):
    return lb.itemcget(index, "foreground")


class _Conn:
    """Ersatz fuer das Objekt, das socket.create_connection liefert."""
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _slow(delay, result, calls=None):
    """Ersatz fuer isdir_fast/isfile_fast: wartet delay Sekunden, liefert result."""
    def f(path):
        if calls is not None:
            calls.append(path)
        time.sleep(delay)
        return result(path) if callable(result) else result
    return f


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def dirs(sandbox):
    """Gute und tote Pfade in der Sandbox."""
    good = os.path.join(sandbox.root, "gut")
    good2 = os.path.join(sandbox.root, "gut2")
    os.makedirs(good)
    os.makedirs(good2)
    cfg = os.path.join(sandbox.root, "test.cfg")
    with open(cfg, "w") as f:
        f.write("x")
    return types.SimpleNamespace(
        good=good, good2=good2,
        dead=os.path.join(sandbox.root, "gibt_es_nicht"),
        cfg=cfg,
        deadfile=os.path.join(sandbox.root, "gibt_es_nicht.cfg"),
    )


@pytest.fixture
def lb(tk_frame):
    box = tk.Listbox(tk_frame, exportselection=False)
    box.pack()
    return box


@pytest.fixture
def label(tk_frame):
    lab = tk.Label(tk_frame, text="DEFAULT")
    lab.pack()
    return lab


# ======================================================================
# _unc_host
# ======================================================================
@pytest.mark.parametrize("path, expected", [
    (r"\\server\share\dir",                 "server"),
    ("//server/share/dir",                  "server"),
    ("//nas.local/foto",                    "nas.local"),
    (r"\\?\C:\x",                           None),   # Sonderform: nicht vorab testen
    (r"\\srv@SSL\dav",                      None),   # WebDAV
    (r"\\fe80--1.ipv6-literal.net\share",   None),   # IPv6-Literal
    ("relativ/pfad",                        None),
    ("",                                    None),
])
def test_unc_host_windows(monkeypatch, path, expected):
    import tools
    monkeypatch.setattr(tools.sys, "platform", "win32")
    assert tools._unc_host(path) == expected


def test_unc_host_is_none_on_non_windows(monkeypatch):
    import tools
    monkeypatch.setattr(tools.sys, "platform", "linux")
    assert tools._unc_host(r"\\server\share") is None


@pytest.mark.skipif(sys.platform != "win32", reason="gemappte Laufwerke nur unter Windows")
def test_unc_host_local_drive_is_none():
    import tools
    system_drive = os.environ.get("SystemDrive", "C:")
    assert tools._unc_host(system_drive + "\\Windows") is None


# ======================================================================
# host_reachable
# ======================================================================
def test_host_reachable_tries_445_then_139(monkeypatch):
    import tools
    tried = []

    def fake(addr, timeout=None):
        tried.append(addr)
        if addr[1] == 139:
            return _Conn()
        raise OSError("refused")
    monkeypatch.setattr(tools.socket, "create_connection", fake)
    assert tools.host_reachable("srv") is True
    assert tried == [("srv", 445), ("srv", 139)]


def test_host_reachable_stops_after_first_success(monkeypatch):
    import tools
    tried = []
    monkeypatch.setattr(tools.socket, "create_connection",
                        lambda addr, timeout=None: tried.append(addr) or _Conn())
    assert tools.host_reachable("srv") is True
    assert tried == [("srv", 445)]


def test_host_reachable_false_when_all_ports_fail(monkeypatch):
    import tools

    def fail(addr, timeout=None):
        raise OSError("timeout")
    monkeypatch.setattr(tools.socket, "create_connection", fail)
    assert tools.host_reachable("srv") is False


# ======================================================================
# isdir_fast / isfile_fast
# ======================================================================
def test_isdir_fast_and_isfile_fast_local(dirs):
    import tools
    assert tools.isdir_fast(dirs.good) is True
    assert tools.isdir_fast(dirs.dead) is False
    assert tools.isdir_fast(dirs.cfg) is False        # Datei ist kein Verzeichnis
    assert tools.isfile_fast(dirs.cfg) is True
    assert tools.isfile_fast(dirs.deadfile) is False
    assert tools.isfile_fast(dirs.good) is False       # Verzeichnis ist keine Datei


@pytest.mark.parametrize("fn_name", ["isdir_fast", "isfile_fast"])
def test_fast_check_skips_filesystem_when_server_unreachable(monkeypatch, dirs, fn_name):
    """Server nicht erreichbar -> False, OHNE os.path.isdir/isfile aufzurufen
    (genau das wuerde bis zum langen Windows-Timeout blockieren)."""
    import tools

    def boom(path):
        raise AssertionError("os.path darf nicht aufgerufen werden")
    monkeypatch.setattr(tools, "_unc_host", lambda p: "srv")
    monkeypatch.setattr(tools, "host_reachable", lambda h, timeout=2.0: False)
    monkeypatch.setattr(tools, "os", types.SimpleNamespace(
        path=types.SimpleNamespace(isdir=boom, isfile=boom)))
    assert getattr(tools, fn_name)(dirs.good) is False


def test_fast_check_falls_through_when_server_reachable(monkeypatch, dirs):
    import tools
    monkeypatch.setattr(tools, "_unc_host", lambda p: "srv")
    monkeypatch.setattr(tools, "host_reachable", lambda h, timeout=2.0: True)
    assert tools.isdir_fast(dirs.good) is True
    assert tools.isdir_fast(dirs.dead) is False
    assert tools.isfile_fast(dirs.cfg) is True
    assert tools.isfile_fast(dirs.deadfile) is False


# ======================================================================
# true_case_path
# ======================================================================
def test_case_walk_applies_lookup_to_every_component():
    """Der Ablauf von true_case_path (plattformunabhaengig): JEDE Komponente wird nachgeschlagen,
    auch die letzte. GetLongPathName allein liess die letzte in der uebergebenen Schreibweise."""
    import tools
    real = {r"c:\arbeit": "Arbeit", r"c:\arbeit\mixedcasedir": "MixedCaseDir"}
    asked = []

    def lookup(partial):
        asked.append(partial)
        return real.get(partial.lower())
    assert tools._case_walk("c:/arbeit/mixedcasedir", lookup) == r"c:\Arbeit\MixedCaseDir"
    assert asked == [r"c:\arbeit", r"c:\Arbeit\mixedcasedir"]   # bereits korrigierter Vorspann


def test_case_walk_keeps_components_without_result_or_with_error():
    import tools

    def lookup(partial):
        if partial.lower().endswith("boom"):
            raise OSError("kaputt")
        return {"x": "X"}.get(partial.rsplit("\\", 1)[-1].lower())
    assert tools._case_walk(r"c:\x\unbekannt\boom\x", lookup) == r"c:\X\unbekannt\boom\X"


def test_case_walk_leaves_drive_and_unc_root_alone():
    import tools
    asked = []

    def lookup(partial):
        asked.append(partial)
        return None
    assert tools._case_walk("//Server/Share/dir", lookup) == r"\\Server\Share\dir"
    assert asked == [r"\\Server\Share\dir"]                       # Server/Share werden nicht abgefragt
    assert tools._case_walk("D:/", lookup) == "D:\\"
    assert tools._case_walk("rel/pfad", lookup) == r"rel\pfad"       # ohne Laufwerk, ohne fuehrendes \


def test_true_case_path_empty_and_missing(dirs):
    import tools
    assert tools.true_case_path("") == ""
    assert tools.true_case_path(dirs.dead) == dirs.dead     # nicht vorhanden: unveraendert


@pytest.mark.skipif(sys.platform == "win32", reason="unter Unix ist die Funktion ein No-op")
def test_true_case_path_is_noop_on_unix(dirs):
    import tools
    assert tools.true_case_path(dirs.good) == dirs.good


@pytest.mark.skipif(sys.platform != "win32", reason="GetLongPathName gibt es nur unter Windows")
def test_true_case_path_restores_case_on_windows(sandbox):
    import tools
    real = os.path.join(sandbox.root, "MixedCaseDir")
    os.makedirs(real)
    wrong = real.lower().replace("\\", "/")          # so liegt der Key in der Listbox
    result = tools.true_case_path(wrong)
    assert result.endswith("/MixedCaseDir"), result
    assert "\\" not in result                          # weiter mit / arbeiten
    assert os.path.normcase(result) == os.path.normcase(real)
    assert result[0].isupper()                         # Laufwerksbuchstabe gross


# ======================================================================
# DirChecker.check_bg
# ======================================================================
def test_check_bg_reports_existence(tk_root, dirchk, dirs, pump):
    got = {}
    dirchk.check_bg(dirs.good, lambda ok: got.__setitem__("good", ok))
    dirchk.check_bg(dirs.dead, lambda ok: got.__setitem__("dead", ok))
    dirchk.check_bg(dirs.cfg, lambda ok: got.__setitem__("cfg", ok), True)
    dirchk.check_bg(dirs.deadfile, lambda ok: got.__setitem__("deadfile", ok), True)
    assert pump(tk_root, lambda: len(got) == 4)
    assert got == {"good": True, "dead": False, "cfg": True, "deadfile": False}


def test_check_bg_does_not_block_the_gui(tk_root, dirchk, dirs, monkeypatch, pump):
    import tools
    monkeypatch.setattr(tools, "isdir_fast", _slow(0.5, True))
    got = []
    t0 = time.time()
    dirchk.check_bg(dirs.good, got.append)
    assert time.time() - t0 < 0.2, "check_bg darf nicht auf die Pruefung warten"
    assert got == []                                   # Ergebnis ist noch nicht da
    assert pump(tk_root, lambda: got == [True])


def test_check_bg_joins_running_check(tk_root, dirchk, dirs, monkeypatch, pump):
    """Zweiter Aufruf waehrend die Pruefung laeuft: Callback anhaengen, KEIN neuer Timeout."""
    import tools
    calls = []
    monkeypatch.setattr(tools, "isdir_fast", _slow(0.3, True, calls))
    order = []
    dirchk.check_bg(dirs.good, lambda ok: order.append(("a", ok)))
    dirchk.check_bg(dirs.good, lambda ok: order.append(("b", ok)))
    assert len(dirchk.pending[dirs.good]) == 2
    assert pump(tk_root, lambda: len(order) == 2)
    assert calls == [dirs.good]                        # nur EIN Pruefaufruf
    assert order == [("a", True), ("b", True)]
    assert dirchk.pending == {}
    # nach Abschluss startet ein neuer Aufruf wieder eine neue Pruefung
    dirchk.check_bg(dirs.good, lambda ok: order.append(("c", ok)))
    assert pump(tk_root, lambda: len(order) == 3)
    assert calls == [dirs.good, dirs.good]


# ======================================================================
# DirChecker.check_list
# ======================================================================
def test_check_list_greys_dead_and_fills_cache(tk_root, dirchk, lb, dirs, pump):
    lb.insert(tk.END, dirs.dead, dirs.good)
    dirchk.check_list(lb, None, [dirs.dead, dirs.good])
    assert pump(tk_root, lambda: len(dirchk.cache) == 2)
    assert dirchk.cache == {dirs.dead: False, dirs.good: True}
    assert color(lb, 0) == "gray"
    assert color(lb, 1) == "black"


def test_check_list_sets_label_to_first_existing(tk_root, dirchk, lb, label, dirs, pump):
    lb.insert(tk.END, dirs.dead, dirs.good, dirs.good2)
    dirchk.check_list(lb, label, [dirs.dead, dirs.good, dirs.good2])
    assert pump(tk_root, lambda: not dirchk.pending)
    assert label.cget("text") == dirs.good             # zweiter Eintrag = erster existierender


def test_check_list_label_waits_for_earlier_entries(tk_root, dirchk, lb, label, dirs, monkeypatch, pump):
    """Ist der oberste Eintrag noch offen (lahmer Netzpfad), darf ein weiter unten stehender,
    schon fertiger Eintrag das Label NICHT setzen - sonst gewinnt die falsche Reihenfolge."""
    import tools
    real = {dirs.dead: False, dirs.good: True, dirs.good2: True}
    monkeypatch.setattr(tools, "isdir_fast",
                        lambda p: (time.sleep(0.5) if p == dirs.good else None) or real[p])
    lb.insert(tk.END, dirs.good, dirs.good2)           # good ist oben, aber langsam
    dirchk.check_list(lb, label, [dirs.good, dirs.good2])
    assert pump(tk_root, lambda: dirs.good2 in dirchk.cache)      # der untere ist fertig
    assert dirs.good not in dirchk.cache                           # der obere noch nicht
    assert label.cget("text") == "DEFAULT"                         # also noch kein Label
    assert pump(tk_root, lambda: not dirchk.pending)
    assert label.cget("text") == dirs.good                         # jetzt der oberste


def test_check_list_keeps_label_the_user_changed(tk_root, dirchk, lb, label, dirs, monkeypatch, pump):
    import tools
    monkeypatch.setattr(tools, "isdir_fast", _slow(0.2, True))
    lb.insert(tk.END, dirs.good)
    dirchk.check_list(lb, label, [dirs.good])
    label.config(text="VOM_BENUTZER")                  # waehrend die Pruefung noch laeuft
    assert pump(tk_root, lambda: not dirchk.pending)
    assert label.cget("text") == "VOM_BENUTZER"


def test_check_list_label_untouched_when_nothing_exists(tk_root, dirchk, lb, label, dirs, pump):
    lb.insert(tk.END, dirs.dead)
    dirchk.check_list(lb, label, [dirs.dead])
    assert pump(tk_root, lambda: not dirchk.pending)
    assert label.cget("text") == "DEFAULT"
    assert color(lb, 0) == "gray"


def test_check_list_with_files(tk_root, dirchk, lb, dirs, pump):
    lb.insert(tk.END, dirs.cfg, dirs.deadfile)
    dirchk.check_list(lb, None, [dirs.cfg, dirs.deadfile], True)
    assert pump(tk_root, lambda: not dirchk.pending)
    assert dirchk.cache == {dirs.cfg: True, dirs.deadfile: False}
    assert (color(lb, 0), color(lb, 1)) == ("black", "gray")


def test_check_list_ignores_destroyed_widget(tk_root, dirchk, dirs, monkeypatch, tk_errors, pump):
    """Widget wird zerstoert, bevor das Ergebnis kommt: keine Exception, nichts bleibt haengen."""
    import tools
    monkeypatch.setattr(tools, "isdir_fast", _slow(0.3, True))
    frame = tk.Frame(tk_root)
    box = tk.Listbox(frame)
    box.insert(tk.END, dirs.good)
    dirchk.check_list(box, None, [dirs.good])
    frame.destroy()
    assert pump(tk_root, lambda: not dirchk.pending)
    assert tk_errors == []
    assert dirchk.cache[dirs.good] is True


# ======================================================================
# DirChecker.check_on_select
# ======================================================================
def test_select_known_dead_is_rejected_immediately(tk_root, dirchk, lb, tk_frame, dirs,
                                                   silence_messageboxes, monkeypatch, pump):
    """Der eigentliche Hauptfall: Meldung SOFORT, auch wenn die Neupruefung lange dauert."""
    import tools
    monkeypatch.setattr(tools, "isdir_fast", _slow(0.4, False))
    lb.insert(tk.END, dirs.dead, dirs.good)
    dirchk.cache[dirs.dead] = False
    lb.selection_set(0)
    t0 = time.time()
    dirchk.check_on_select(lb, "Indir", parent=tk_frame, title="error")
    assert time.time() - t0 < 0.2
    # sofort - ohne dass die Eventloop gelaufen waere:
    assert lb.curselection() == ()
    assert len(silence_messageboxes) == 1
    kind, args, kwargs = silence_messageboxes[0]
    assert kind == "error"
    assert args[0] == "error"
    assert "Indir" in args[1] and dirs.dead in args[1]
    assert kwargs == {"parent": tk_frame}
    assert pump(tk_root, lambda: not dirchk.pending)   # Neupruefung im Hintergrund
    assert len(silence_messageboxes) == 1              # und keine zweite Meldung


def test_select_default_title_and_no_parent(tk_root, dirchk, lb, dirs, silence_messageboxes, pump):
    lb.insert(tk.END, dirs.dead)
    dirchk.cache[dirs.dead] = False
    lb.selection_set(0)
    dirchk.check_on_select(lb, "outdir")
    kind, args, kwargs = silence_messageboxes[0]
    assert args[0] == "showerror"
    assert kwargs == {}                                # kein parent=None durchreichen
    pump(tk_root, lambda: not dirchk.pending)


def test_select_unknown_dead_is_deselected_after_check(tk_root, dirchk, lb, dirs,
                                                       silence_messageboxes, monkeypatch, pump):
    import tools
    monkeypatch.setattr(tools, "isdir_fast", _slow(0.3, False))
    lb.insert(tk.END, dirs.dead)
    lb.selection_set(0)
    dirchk.check_on_select(lb, "Indir")
    # solange geprueft wird: GUI frei, Auswahl noch da, noch keine Meldung
    assert lb.curselection() == (0,)
    assert silence_messageboxes == []
    assert pump(tk_root, lambda: len(silence_messageboxes) == 1)
    assert lb.curselection() == ()
    assert dirchk.cache[dirs.dead] is False
    assert color(lb, 0) == "gray"


def test_select_existing_keeps_selection_without_message(tk_root, dirchk, lb, dirs,
                                                         silence_messageboxes, pump):
    lb.insert(tk.END, dirs.good)
    lb.selection_set(0)
    dirchk.check_on_select(lb, "Indir")
    assert pump(tk_root, lambda: not dirchk.pending)
    assert lb.curselection() == (0,)
    assert silence_messageboxes == []
    assert dirchk.cache[dirs.good] is True


def test_select_known_good_does_not_wait(tk_root, dirchk, lb, dirs, silence_messageboxes, pump):
    """Bekannt vorhandener Eintrag: Auswahl bleibt sofort, es wird nur im Hintergrund bestaetigt."""
    lb.insert(tk.END, dirs.good)
    dirchk.cache[dirs.good] = True
    lb.selection_set(0)
    dirchk.check_on_select(lb, "Indir")
    assert lb.curselection() == (0,)
    assert silence_messageboxes == []
    pump(tk_root, lambda: not dirchk.pending)


def test_select_known_good_but_gone_now(tk_root, dirchk, lb, dirs, silence_messageboxes,
                                        monkeypatch, pump):
    """Cache sagt 'vorhanden', die Hintergrundpruefung stellt fest: inzwischen weg."""
    import tools
    monkeypatch.setattr(tools, "isdir_fast", _slow(0.1, False))
    lb.insert(tk.END, dirs.good)
    dirchk.cache[dirs.good] = True
    lb.selection_set(0)
    dirchk.check_on_select(lb, "Indir")
    assert pump(tk_root, lambda: len(silence_messageboxes) == 1)
    assert lb.curselection() == ()
    assert dirchk.cache[dirs.good] is False
    assert color(lb, 0) == "gray"


def test_select_known_dead_recovers_when_server_is_back(tk_root, dirchk, lb, dirs,
                                                        silence_messageboxes, pump):
    """Eintrag war grau/tot, ist jetzt aber wieder da: erste Klick meldet noch (Cache), laeuft
    aber im Hintergrund neu -> Eintrag wird schwarz, der naechste Klick funktioniert."""
    lb.insert(tk.END, dirs.good)                       # existiert tatsaechlich
    lb.itemconfig(0, fg="gray")
    dirchk.cache[dirs.good] = False
    lb.selection_set(0)
    dirchk.check_on_select(lb, "Indir")
    assert len(silence_messageboxes) == 1              # sofortige Meldung aus dem Cache
    assert pump(tk_root, lambda: dirchk.cache[dirs.good] is True)
    assert color(lb, 0) == "black"
    lb.selection_set(0)                                # zweiter Klick
    dirchk.check_on_select(lb, "Indir")
    assert pump(tk_root, lambda: not dirchk.pending)
    assert len(silence_messageboxes) == 1              # keine weitere Meldung
    assert lb.curselection() == (0,)


def test_select_with_files(tk_root, dirchk, lb, dirs, silence_messageboxes, pump):
    lb.insert(tk.END, dirs.deadfile, dirs.cfg)
    lb.selection_set(0)
    dirchk.check_on_select(lb, "Configfile", title="error", isfile=True)
    assert pump(tk_root, lambda: len(silence_messageboxes) == 1)
    assert silence_messageboxes[0][1][0] == "error"
    assert "Configfile" in silence_messageboxes[0][1][1]
    assert lb.curselection() == ()
    lb.selection_set(1)                                # existierende Datei
    dirchk.check_on_select(lb, "Configfile", title="error", isfile=True)
    assert pump(tk_root, lambda: not dirchk.pending)
    assert len(silence_messageboxes) == 1
    assert lb.curselection() == (1,)


def test_select_without_selection_is_ignored(tk_root, dirchk, lb, dirs, silence_messageboxes):
    lb.insert(tk.END, dirs.good)
    dirchk.check_on_select(lb, "Indir")                # nichts selektiert: kein IndexError
    assert silence_messageboxes == []
    assert dirchk.pending == {}


# ======================================================================
# DirChecker.select_in_listbox
# ======================================================================
def test_select_in_listbox_inserts_new_entry_on_top(tk_root, dirchk, lb):
    lb.insert(tk.END, "c:/alt")
    dirchk.select_in_listbox(lb, "C:\\Neu")
    assert lb.get(0, tk.END) == ("c:/neu", "c:/alt")   # normalisiert, ganz oben
    assert lb.curselection() == (0,)
    assert dirchk.cache["c:/neu"] is True              # kam aus dem Dateidialog


def test_select_in_listbox_reuses_existing_entry_case_insensitive(tk_root, dirchk, lb):
    lb.insert(tk.END, "c:/neu", "c:/alt")
    dirchk.select_in_listbox(lb, "C:/ALT")
    assert lb.get(0, tk.END) == ("c:/neu", "c:/alt")   # kein Duplikat
    assert lb.curselection() == (1,)
    assert dirchk.cache["c:/alt"] is True


def test_select_in_listbox_clears_grey_and_old_selection(tk_root, dirchk, lb):
    lb.insert(tk.END, "c:/neu", "c:/alt")
    lb.itemconfig(1, fg="gray")
    lb.selection_set(0)
    dirchk.select_in_listbox(lb, "c:/alt")
    assert color(lb, 1) == "black"                     # war ausgegraut, existiert aber jetzt
    assert lb.curselection() == (1,)                   # alte Auswahl aufgehoben


def test_select_in_listbox_on_empty_listbox(tk_root, dirchk, lb):
    dirchk.select_in_listbox(lb, "D:/erstes")
    assert lb.get(0, tk.END) == ("d:/erstes",)
    assert lb.curselection() == (0,)


# ======================================================================
# DirChecker.mark
# ======================================================================
def test_mark_updates_cache_and_colour(tk_root, dirchk, lb):
    lb.insert(tk.END, "x", "y")
    dirchk.mark(lb, "y", False)
    assert dirchk.cache["y"] is False and color(lb, 1) == "gray" and color(lb, 0) == ""
    dirchk.mark(lb, "y", True)
    assert dirchk.cache["y"] is True and color(lb, 1) == "black"
