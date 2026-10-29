# -*- coding: utf-8 -*-
"""
test_support_dirs.py - Regressionstests fuer Methoden von Dateimeister_support, die wir
repariert bzw. neu gebaut haben:

    Button_generate_pressed   Cache-Zweig nur, wenn Globals.generated gesetzt ist
                              (Fehler: Kamera A -> B -> A, dann Generate zeigte
                              "keine Daten" und generierte nichts)
    Press_indir/Press_outdir  neues Verzeichnis sofort in Listbox + XML, selektiert,
                              Abbruch laesst alles unveraendert
    new_dir_in_xml            Aufraeumen ohne blockierende Dateisystemzugriffe
    _combined_key             Schluessel unabhaengig von der Klickreihenfolge

Die Support-Klasse baut beim Start das komplette GUI auf. Hier werden die Methoden deshalb
UNGEBUNDEN gegen ein kleines Stub-Objekt aufgerufen (Dateimeister_support.Dateimeister_support
.<methode>(stub)). Widgets sind echt (tk_root), alles andere (XML, Dialog, Generate, Anzeige)
ist gestubbt bzw. protokolliert.

Hinweis: Der Import von Dateimeister_support setzt auf Modulebene sys.excepthook und
tk.Tk.report_callback_exception (siehe dort) und aktiviert faulthandler. Das betrifft die
Tests nicht, ist aber ein globaler Seiteneffekt des Imports.

Fuer Linux: xvfb-run pytest
"""

import importlib
import re
import types
import tkinter as tk

import pytest


# ----------------------------------------------------------------------
# Hilfen (tk_frame und dirchk kommen aus conftest.py)
# ----------------------------------------------------------------------
@pytest.fixture(scope="module")
def S():
    """Das Modul Dateimeister_support (echter Import)."""
    return importlib.import_module("Dateimeister_support")


@pytest.fixture
def Cls(S):
    return S.Dateimeister_support


@pytest.fixture
def gstate(monkeypatch):
    """Globals-Zustand, den Button_generate_pressed liest/schreibt; wird nach dem Test zurueckgesetzt."""
    import tools
    monkeypatch.setattr(tools.Globals, "generated", False, raising=False)
    monkeypatch.setattr(tools.Globals, "imagetype", "", raising=False)
    monkeypatch.setattr(tools.Globals, "imagetypes_selected", [], raising=False)
    return tools.Globals


# ======================================================================
# _combined_key
# ======================================================================
def test_combined_key(Cls):
    assert Cls._combined_key([]) == ""
    assert Cls._combined_key(["JPEG"]) == "JPEG"
    assert Cls._combined_key(["VIDEO", "JPEG", "RAW"]) == "JPEG-RAW-VIDEO"
    # unabhaengig von der Klickreihenfolge
    assert Cls._combined_key(["RAW", "VIDEO"]) == Cls._combined_key(["VIDEO", "RAW"])


# ======================================================================
# Button_generate_pressed
# ======================================================================
class _Var:
    def __init__(self, v=""):
        self.v = v

    def set(self, v):
        self.v = v

    def get(self):
        return self.v


class _LB:
    def __init__(self, selected, size):
        self._sel, self._size = tuple(selected), size

    def curselection(self):
        return self._sel

    def size(self):
        return self._size


def make_generate_stub(Cls, selected=(0, 1, 2), keys=("JPEG", "RAW", "VIDEO"),
                       click_order=None, source_target=None):
    """Stub mit den Attributen, die Button_generate_pressed braucht. Die Methoden, die Generate
    und Anzeige ausloesen, sind Rekorder."""
    calls = []
    ns = types.SimpleNamespace(
        debug=False,
        lb_gen=_LB(selected, len(keys)),
        dict_gen_files_keys=list(keys),
        imagetypes_click_order=list(click_order if click_order is not None else selected),
        rbg=_Var("2"), rbvalue=_Var("2"),
        dict_source_target=dict(source_target or {}),
        dict_sort_method={},
        calls=calls,
    )
    ns._get_selected_types = types.MethodType(Cls._get_selected_types, ns)
    ns._combined_key = Cls._combined_key
    ns.generate = lambda: calls.append("generate")
    ns.display_images_prepare = lambda: calls.append("display")
    ns._sort_within_types = lambda key, sm: calls.append(("sort_within", key, sm))
    ns.resort = lambda key, sm: calls.append(("resort", key, sm))
    return ns


def test_generate_without_selection_shows_message(Cls, gstate, silence_messageboxes):
    ns = make_generate_stub(Cls, selected=())
    assert Cls.Button_generate_pressed(ns) is None
    assert ns.calls == []                                  # weder Generate noch Anzeige
    kinds = [c[0] for c in silence_messageboxes]
    assert kinds == ["info"]
    assert "No type selected" in silence_messageboxes[0][1][1]


def test_generate_first_time_runs_full_generate(Cls, gstate):
    gstate.generated = True                                # alter Zustand, wird zurueckgesetzt
    ns = make_generate_stub(Cls, selected=(0,))            # JPEG, noch nicht in dict_source_target
    seen = []
    ns.generate = lambda: seen.append(gstate.generated) or ns.calls.append("generate")
    Cls.Button_generate_pressed(ns)
    assert ns.calls == ["generate"]
    assert seen == [False]                                 # generate() sieht generated == False


def test_generate_cached_when_generated_and_key_present(Cls, gstate):
    """Gleiche Auswahl nochmal: kein neuer Scan, nur sortieren + anzeigen."""
    gstate.generated = True
    ns = make_generate_stub(Cls, selected=(0, 1, 2), click_order=[2, 0, 1],
                            source_target={"JPEG-RAW-VIDEO": {"a.jpg": "b.jpg"}})
    Cls.Button_generate_pressed(ns)
    assert "generate" not in ns.calls
    assert ns.calls == [("sort_within", "JPEG-RAW-VIDEO", 1), "display"]
    assert gstate.imagetype == "JPEG-RAW-VIDEO"            # <- fehlte, daher die Message Box
    assert gstate.imagetypes_selected == ["VIDEO", "JPEG", "RAW"]   # Klickreihenfolge
    assert ns.dict_sort_method["JPEG-RAW-VIDEO"] == "1"


def test_generate_after_camera_switch_does_a_fresh_generate(Cls, gstate):
    """DER Regressionsfall: A generiert, Wechsel zu B und zurueck zu A (Globals.generated ist
    dabei False geworden, dict_source_target enthaelt den Schluessel von A noch). Der Cache-Zweig
    darf NICHT genommen werden - sonst ist Globals.imagetype leer und es wird nichts angezeigt."""
    gstate.generated = False
    gstate.imagetype = ""                                  # B_camera_press setzt das zurueck
    ns = make_generate_stub(Cls, selected=(0, 1, 2),
                            source_target={"JPEG-RAW-VIDEO": {"a.jpg": "b.jpg"}})
    Cls.Button_generate_pressed(ns)
    assert ns.calls == ["generate"]                        # voller Pfad, keine direkte Anzeige
    assert "display" not in ns.calls


def test_generate_different_selection_is_not_cached(Cls, gstate):
    gstate.generated = True
    ns = make_generate_stub(Cls, selected=(0,), source_target={"JPEG-RAW-VIDEO": {}})
    Cls.Button_generate_pressed(ns)
    assert ns.calls == ["generate"]


def test_generate_resets_sort_radio_buttons(Cls, gstate):
    gstate.generated = True
    ns = make_generate_stub(Cls, selected=(0,), source_target={"JPEG": {}})
    Cls.Button_generate_pressed(ns)
    assert (ns.rbg.get(), ns.rbvalue.get()) == ("1", "1")


# ======================================================================
# Press_indir / Press_outdir
# ======================================================================
def make_press_stub(tk_frame, dirchk, old_in="", old_out=""):
    calls = {"xml": [], "gen_required": 0}
    ns = types.SimpleNamespace(debug=False, dirchk=dirchk, max_indirs=10, max_outdirs=7)
    for kind, old in (("indir", old_in), ("outdir", old_out)):
        setattr(ns, "listbox_" + kind, tk.Listbox(tk_frame, exportselection=False))
        setattr(ns, "label_" + kind, tk.Label(tk_frame, text=old))
        setattr(ns, "button_%s_from_list" % kind, tk.Button(tk_frame, state=tk.DISABLED))
    ns.new_dir_in_xml = lambda *a: calls["xml"].append(a)

    def gen_required():
        calls["gen_required"] += 1
    ns.state_gen_required = gen_required
    ns.calls = calls
    return ns


def dialog(monkeypatch, S, value):
    monkeypatch.setattr(S.fd, "askdirectory", lambda *a, **k: value)


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_press_new_dir_appears_selected_and_is_saved(S, Cls, tk_root, tk_frame, dirchk,
                                                     monkeypatch, kind):
    ns = make_press_stub(tk_frame, dirchk, old_in="c:/alt", old_out="d:/alt")
    lb = getattr(ns, "listbox_" + kind)
    lb.insert(tk.END, "c:/bestehend")
    dialog(monkeypatch, S, "C:\\Fotos\\Neu")
    getattr(Cls, "Press_" + kind)(ns)

    assert lb.get(0, tk.END) == ("c:/fotos/neu", "c:/bestehend")   # neu ganz oben, normalisiert
    assert lb.curselection() == (0,)                                 # und selektiert
    assert getattr(ns, "label_" + kind).cget("text") == "C:\\Fotos\\Neu"   # Label: gewaehlter Text
    assert str(getattr(ns, "button_%s_from_list" % kind).cget("state")) == "normal"
    # sofort in der XML (sonst waere der Eintrag nach einem Neustart weg)
    assert len(ns.calls["xml"]) == 1
    typ, maxdirs, name, ts = ns.calls["xml"][0]
    assert typ == kind
    assert maxdirs == (10 if kind == "indir" else 7)
    assert name == "c:/fotos/neu"
    assert re.fullmatch(r"\d{8}-\d{2}:\d{2}:\d{2}", ts), ts
    assert ns.calls["gen_required"] == 1                             # Verzeichnis hat gewechselt


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_press_existing_dir_is_reused_not_duplicated(S, Cls, tk_root, tk_frame, dirchk,
                                                     monkeypatch, kind):
    ns = make_press_stub(tk_frame, dirchk, old_in="x", old_out="x")
    lb = getattr(ns, "listbox_" + kind)
    lb.insert(tk.END, "c:/eins", "c:/zwei")
    dialog(monkeypatch, S, "C:/ZWEI")                                # andere Schreibweise
    getattr(Cls, "Press_" + kind)(ns)
    assert lb.get(0, tk.END) == ("c:/eins", "c:/zwei")               # kein Duplikat
    assert lb.curselection() == (1,)
    assert [c[2] for c in ns.calls["xml"]] == ["c:/zwei"]            # usedate in der XML aktualisieren


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_press_cancel_changes_nothing(S, Cls, tk_root, tk_frame, dirchk, monkeypatch, kind):
    """Abbrechen im Dateidialog: frueher wurde das Label geleert."""
    ns = make_press_stub(tk_frame, dirchk, old_in="c:/alt", old_out="d:/alt")
    lb = getattr(ns, "listbox_" + kind)
    lb.insert(tk.END, "c:/eins")
    dialog(monkeypatch, S, "")
    assert getattr(Cls, "Press_" + kind)(ns) is None
    assert getattr(ns, "label_" + kind).cget("text") == ("c:/alt" if kind == "indir" else "d:/alt")
    assert lb.get(0, tk.END) == ("c:/eins",)
    assert lb.curselection() == ()
    assert ns.calls == {"xml": [], "gen_required": 0}


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_press_same_dir_does_not_invalidate_generated_data(S, Cls, tk_root, tk_frame, dirchk,
                                                           monkeypatch, kind):
    """Gleiches Verzeichnis nochmal gewaehlt: kein state_gen_required (sonst gingen die
    erzeugten Daten ohne Grund verloren), aber die XML wird trotzdem aktualisiert."""
    ns = make_press_stub(tk_frame, dirchk, old_in="C:/Gleich", old_out="C:/Gleich")
    dialog(monkeypatch, S, "C:/Gleich")
    getattr(Cls, "Press_" + kind)(ns)
    assert ns.calls["gen_required"] == 0
    assert len(ns.calls["xml"]) == 1


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_press_first_selection_with_empty_label_requires_generate(S, Cls, tk_root, tk_frame,
                                                                  dirchk, monkeypatch, kind):
    ns = make_press_stub(tk_frame, dirchk, old_in="", old_out="")
    dialog(monkeypatch, S, "C:/Erstes")
    getattr(Cls, "Press_" + kind)(ns)
    assert ns.calls["gen_required"] == 1


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_press_greyed_entry_becomes_usable_again(S, Cls, tk_root, tk_frame, dirchk, monkeypatch, kind):
    ns = make_press_stub(tk_frame, dirchk, old_in="x", old_out="x")
    lb = getattr(ns, "listbox_" + kind)
    lb.insert(tk.END, "c:/zwei")
    lb.itemconfig(0, fg="gray")                                      # war tot, Dialog liefert es jetzt
    dialog(monkeypatch, S, "c:/zwei")
    getattr(Cls, "Press_" + kind)(ns)
    assert lb.itemcget(0, "foreground") == "black"
    assert dirchk.cache["c:/zwei"] is True


# ======================================================================
# new_dir_in_xml
# ======================================================================
class FakeXml:
    """Ersatz fuer die XML-Funktionen von dateimeister_config_xml (DX)."""
    def __init__(self, entries):          # {"dir": "usedate"}
        self.d = {k: {"usedate": v} for k, v in entries.items()}
        self.deleted, self.created = [], []

    def get(self, xml):
        return {k: dict(v) for k, v in self.d.items()}

    def delete(self, xml, name):
        self.d.pop(name)
        self.deleted.append(name)

    def new_indir(self, xml, name, a, b, ts, n):
        self.d[name] = {"usedate": ts}
        self.created.append(("indir", name, ts))

    def new_outdir(self, xml, name, ts):
        self.d[name] = {"usedate": ts}
        self.created.append(("outdir", name, ts))


@pytest.fixture
def fakexml(S, monkeypatch):
    import tools

    def install(entries):
        fx = FakeXml(entries)
        monkeypatch.setattr(S.DX, "get_indirs", fx.get)
        monkeypatch.setattr(S.DX, "get_outdirs", fx.get)
        monkeypatch.setattr(S.DX, "delete_indir", fx.delete)
        monkeypatch.setattr(S.DX, "delete_outdir", fx.delete)
        monkeypatch.setattr(S.DX, "new_indir", fx.new_indir)
        monkeypatch.setattr(S.DX, "new_outdir", fx.new_outdir)
        monkeypatch.setattr(tools.Globals, "config_files_xml", "fake.xml", raising=False)
        return fx
    return install


def five_dirs():
    # e1 ist am aeltesten, e5 am neuesten
    return {"e%d" % i: "2026010%d-10:00:00" % i for i in range(1, 6)}


def cleanup_stub(cache=None):
    return types.SimpleNamespace(debug=False, dirchk=types.SimpleNamespace(cache=dict(cache or {})))


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_xml_existing_dir_only_updates_usedate(S, Cls, fakexml, kind):
    fx = fakexml(five_dirs())
    Cls.new_dir_in_xml(cleanup_stub({"e1": False}), kind, 5, "e3", "20260301-00:00:00")
    assert fx.deleted == []                                # existierender Eintrag: kein Aufraeumen
    assert fx.created == [(kind, "e3", "20260301-00:00:00")]


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_xml_under_limit_deletes_nothing(S, Cls, fakexml, kind):
    fx = fakexml(five_dirs())
    Cls.new_dir_in_xml(cleanup_stub(), kind, 6, "neu", "20260301-00:00:00")
    assert fx.deleted == []
    assert fx.created == [(kind, "neu", "20260301-00:00:00")]


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_xml_over_limit_deletes_oldest_known_dead_first(S, Cls, fakexml, kind):
    fx = fakexml(five_dirs())
    # e1 (aeltester) existiert, e2 und e4 sind bekannt tot: es muss genau EIN Eintrag weg
    # (max 5, neu dazu), und zwar der aelteste tote - nicht der aelteste ueberhaupt.
    Cls.new_dir_in_xml(cleanup_stub({"e1": True, "e2": False, "e4": False}),
                       kind, 5, "neu", "20260301-00:00:00")
    assert fx.deleted == ["e2"]


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_xml_over_limit_without_dead_deletes_oldest_existing(S, Cls, fakexml, kind):
    fx = fakexml(five_dirs())
    Cls.new_dir_in_xml(cleanup_stub({"e%d" % i: True for i in range(1, 6)}),
                       kind, 5, "neu", "20260301-00:00:00")
    assert fx.deleted == ["e1"]


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_xml_deletes_dead_first_then_oldest_existing_up_to_limit(S, Cls, fakexml, kind):
    fx = fakexml(five_dirs())
    # max 3, neu dazu -> 3 muessen weg: e4 (tot) zuerst, dann die aeltesten vorhandenen e1, e2
    Cls.new_dir_in_xml(cleanup_stub({"e4": False}), kind, 3, "neu", "20260301-00:00:00")
    assert fx.deleted == ["e4", "e1", "e2"]
    assert sorted(fx.d) == ["e3", "e5", "neu"]


@pytest.mark.parametrize("kind", ["indir", "outdir"])
def test_xml_unknown_entries_count_as_existing_without_filesystem_access(S, Cls, fakexml,
                                                                         monkeypatch, kind):
    """Eintraege ohne Ergebnis im Cache gelten als vorhanden. Es darf KEIN Dateisystemzugriff
    stattfinden (ein toter Netzpfad wuerde bis zum Timeout blockieren)."""
    fx = fakexml(five_dirs())

    def boom(p):
        raise AssertionError("Dateisystemzugriff in new_dir_in_xml: %r" % p)
    monkeypatch.setattr(S, "os", types.SimpleNamespace(
        path=types.SimpleNamespace(isdir=boom, isfile=boom, exists=boom)))
    Cls.new_dir_in_xml(cleanup_stub(), kind, 5, "neu", "20260301-00:00:00")
    assert fx.deleted == ["e1"]
