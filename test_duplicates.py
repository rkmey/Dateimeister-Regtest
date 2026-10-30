# -*- coding: utf-8 -*-
"""
Regressionstests fuer MyDuplicates (Dateimeister_Duplicates.py).

Getestet werden:
  * Konstruktion: Fenstertitel, Listbox-Befuellung, Event-Registrierung,
    Caller-Button auf DISABLED
  * lb_double / dupl_handler: Auswahl einer Dublette, thisduplicate setzen,
    display_duplicate aufrufen
  * display_duplicate: Canvas fuellen, Thumbnails anlegen, State uebernehmen,
    dict_thumbnails_duplicates fuellen, Scrollregion setzen
  * (weitere Bloecke in spaeteren Ergaenzungen)

Nicht getestet:
  * die tatsaechliche Bilddarstellung auf dem Canvas
  * Video-Player-Details (kommt in einem eigenen Block)
  * die Tooltip-Logik im Detail
"""

import os

import pytest

from tools import INCLUDE, EXCLUDE, FileStateEvent, ClosingEvent, PrintRequestEvent


# ======================================================================
# Block A: Fixtures
#
# (alle Fixtures stehen in conftest.py: dummy_support_caller,
#  duplicates_globals, duplicates_window, MiniThumbnail.is_broken)
# ======================================================================


# ======================================================================
# Block B: Konstruktion
# ======================================================================

def test_constructor_creates_window(duplicates_window):
    """MyDuplicates legt ein Toplevel-Fenster an."""
    win, caller, info = duplicates_window
    assert win.root is not None
    assert win.root.winfo_exists()


def test_constructor_title_contains_imagetype(duplicates_window):
    """Der Fenstertitel enthaelt Globals.imagetype."""
    win, caller, info = duplicates_window
    import tools
    assert tools.Globals.imagetype in win.root.title()


def test_constructor_populates_listbox_from_dict_duplicates(
        duplicates_window):
    """Die Listbox wird aus Globals.dict_duplicates[imagetype] gefuellt."""
    win, caller, info = duplicates_window
    items = list(win.lb_duplicates.get(0, "end"))
    assert info["target"] in items
    # erste Zeile ist automatisch selektiert
    assert win.lb_duplicates.curselection() == (0,)


def test_constructor_disables_caller_button(duplicates_window):
    """Der Caller-Button 'duplicates' wird auf DISABLED gesetzt."""
    win, caller, info = duplicates_window
    import tkinter as tk
    assert str(caller.button_duplicates.cget("state")) == str(tk.DISABLED)


def test_constructor_registers_events(duplicates_window, globals_event_manager):
    """FileStateChanged und Closing sind registriert."""
    win, caller, info = duplicates_window
    listeners = globals_event_manager.listeners
    assert "FileStateChanged" in listeners
    assert win.on_file_state_changed in listeners["FileStateChanged"]
    assert "Closing" in listeners
    assert win.on_closing in listeners["Closing"]


def test_constructor_thisduplicate_initially_none(duplicates_window):
    """thisduplicate ist beim Oeffnen noch None."""
    win, caller, info = duplicates_window
    assert win.thisduplicate is None


def test_constructor_thumbnails_duplicates_empty(duplicates_window):
    """Vor der ersten Auswahl ist thumbnails_duplicates leer."""
    win, caller, info = duplicates_window
    assert win.thumbnails_duplicates == {}
    assert win.dict_thumbnails_duplicates == {}


# ======================================================================
# Block C: lb_double / dupl_handler
# ======================================================================

def test_lb_double_sets_thisduplicate(duplicates_window):
    """lb_double liest die ausgewaehlte Zeile in thisduplicate."""
    win, caller, info = duplicates_window
    win.lb_duplicates.selection_clear(0, "end")
    win.lb_duplicates.selection_set(0)
    win.lb_double(None)
    assert win.thisduplicate == info["target"]


def test_lb_double_calls_display_duplicate(duplicates_window, monkeypatch):
    """lb_double ruft display_duplicate mit dem Zielnamen."""
    win, caller, info = duplicates_window
    calls = []
    monkeypatch.setattr(win, "display_duplicate", lambda t: calls.append(t))
    win.lb_duplicates.selection_clear(0, "end")
    win.lb_duplicates.selection_set(0)
    win.lb_double(None)
    assert calls == [info["target"]]


def test_dupl_handler_sets_thisduplicate(duplicates_window):
    """dupl_handler liest die ausgewaehlte Zeile in thisduplicate."""
    win, caller, info = duplicates_window
    win.lb_duplicates.selection_clear(0, "end")
    win.lb_duplicates.selection_set(0)
    win.dupl_handler()
    assert win.thisduplicate == info["target"]


def test_dupl_handler_calls_display_duplicate(duplicates_window, monkeypatch):
    """dupl_handler ruft display_duplicate mit dem Zielnamen."""
    win, caller, info = duplicates_window
    calls = []
    monkeypatch.setattr(win, "display_duplicate", lambda t: calls.append(t))
    win.lb_duplicates.selection_clear(0, "end")
    win.lb_duplicates.selection_set(0)
    win.dupl_handler()
    assert calls == [info["target"]]


def test_dupl_handler_calls_stop_all_players(duplicates_window):
    """dupl_handler ruft stop_all_players() auf dem Caller."""
    win, caller, info = duplicates_window
    win.lb_duplicates.selection_clear(0, "end")
    win.lb_duplicates.selection_set(0)
    caller.stop_all_players_calls = 0
    win.dupl_handler()
    # display_duplicate ruft stop_all_players; dupl_handler ruft es ebenfalls.
    assert caller.stop_all_players_calls >= 1


# ======================================================================
# Block D: display_duplicate
# ======================================================================

def test_display_duplicate_creates_thumbnails(duplicates_window):
    """display_duplicate legt fuer jede Quelldatei ein Thumbnail an."""
    win, caller, info = duplicates_window
    win.thisduplicate = info["target"]
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    assert len(win.thumbnails_duplicates[imagetype]) == len(info["sources"])


def test_display_duplicate_fills_dict_thumbnails_duplicates(duplicates_window):
    """dict_thumbnails_duplicates enthaelt genau die Quelldateien."""
    win, caller, info = duplicates_window
    win.thisduplicate = info["target"]
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    keys = set(win.dict_thumbnails_duplicates[imagetype].keys())
    assert keys == set(info["sources"])


def test_display_duplicate_sets_scrollregion(duplicates_window):
    """Nach display_duplicate ist eine Scrollregion gesetzt."""
    win, caller, info = duplicates_window
    win.thisduplicate = info["target"]
    win.display_duplicate(info["target"])
    bbox = win.f.bbox("all")
    assert bbox is not None
    assert bbox[2] > 0  # rechte Kante > 0


def test_display_duplicate_clears_canvas_first(duplicates_window):
    """Ein zweiter Aufruf loescht die vorhandenen Canvas-Items."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    count_before = len(win.f.find_all())
    win.display_duplicate(info["target"])
    count_after = len(win.f.find_all())
    # dieselbe Anzahl, weil der Canvas neu aufgebaut wird
    assert count_after == count_before


def test_display_duplicate_inherits_state(duplicates_window):
    """Der State der Quelldatei wird auf das Duplikat-Thumbnail uebernommen."""
    win, caller, info = duplicates_window
    imagetype = info["imagetype"]
    # erste Quelldatei auf EXCLUDE setzen
    first = info["sources"][0]
    import tools
    tools.Globals.dict_thumbnails[imagetype][first].setState(EXCLUDE)

    win.display_duplicate(info["target"])

    dup_thumb = win.dict_thumbnails_duplicates[imagetype][first]
    assert dup_thumb.getState() == EXCLUDE


def test_display_duplicate_sets_lastposition(duplicates_window):
    """Nach display_duplicate ist lastposition gesetzt."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    assert win.lastposition > 0


def test_display_duplicate_num_images_matches_sources(duplicates_window):
    """num_images entspricht der Anzahl der Quelldateien."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    assert win.num_images == len(info["sources"])


def test_display_duplicate_empty_list_does_nothing(duplicates_window):
    """Leere Quelldatei-Liste -> keine Thumbnails, keine Exception."""
    win, caller, info = duplicates_window
    import tools
    imagetype = info["imagetype"]
    target = "EMPTY_TARGET.JPG"
    tools.Globals.dict_duplicates[imagetype][target] = []

    win.display_duplicate(target)

    assert win.thumbnails_duplicates[imagetype] == []
    assert win.num_images == 0
    
# ======================================================================
# Block E: Include / Exclude
# ======================================================================

class _FakeMouseEvent:
    """Minimales Event-Objekt fuer canvas_exclude / canvas_show / etc."""
    def __init__(self, x=0, y=0, x_root=0, y_root=0):
        self.x = x
        self.y = y
        self.x_root = x_root
        self.y_root = y_root


def _click_on_first_thumbnail(win):
    """Liefert ein _FakeMouseEvent, das auf das erste Duplikat-Thumbnail zeigt."""
    thumb = win.thumbnails_duplicates[win.thisduplicate_imagetype()][0] \
        if hasattr(win, "thisduplicate_imagetype") else None
    # kein Zwischenweg ueber eine Hilfsmethode: direkt die erste Thumbnail-Position nehmen
    thumbs = win.thumbnails_duplicates[next(iter(win.thumbnails_duplicates))]
    t = thumbs[0]
    x = t.getStart() + 5
    y = 5
    return _FakeMouseEvent(x, y)


def test_canvas_exclude_toggles_include_to_exclude(
        duplicates_window, globals_event_manager):
    """INCLUDE -> EXCLUDE: Event mit state=EXCLUDE wird gefeuert."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]

    first = info["sources"][0]
    assert win.dict_thumbnails_duplicates[imagetype][first].getState() == INCLUDE

    events = []
    globals_event_manager.bind("FileStateChanged", lambda e: events.append(e))

    ev = _FakeMouseEvent(x=5, y=5)
    win.canvas_exclude(ev)

    # unser Event ist da (andere koennten zusaetzlich gefeuert werden, ist aber nicht so)
    our = [e for e in events
           if isinstance(e, FileStateEvent) and e.filename == first]
    assert len(our) == 1
    assert our[0].state == EXCLUDE


def test_canvas_exclude_toggles_exclude_to_include(
        duplicates_window, globals_event_manager):
    """EXCLUDE -> INCLUDE: Event mit state=INCLUDE wird gefeuert."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]

    first = info["sources"][0]
    # Vorab auf EXCLUDE setzen (auch im Thumbnail-State)
    import tools
    tools.Globals.dict_thumbnails[imagetype][first].setState(EXCLUDE)
    win.dict_thumbnails_duplicates[imagetype][first].setState(EXCLUDE)

    events = []
    globals_event_manager.bind("FileStateChanged", lambda e: events.append(e))

    ev = _FakeMouseEvent(x=5, y=5)
    win.canvas_exclude(ev)

    our = [e for e in events
           if isinstance(e, FileStateEvent) and e.filename == first]
    assert len(our) == 1
    assert our[0].state == INCLUDE


def test_canvas_exclude_no_hit_no_event(
        duplicates_window, globals_event_manager):
    """Klick ausserhalb jedes Thumbnails -> kein FileStateEvent."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])

    events = []
    globals_event_manager.bind("FileStateChanged", lambda e: events.append(e))

    # weit hinter dem letzten Thumbnail
    last = win.thumbnails_duplicates[info["imagetype"]][-1]
    ev = _FakeMouseEvent(x=last.getEnd() + 1000, y=5)
    win.canvas_exclude(ev)

    our = [e for e in events if isinstance(e, FileStateEvent)]
    assert our == []


def test_canvas_image_exclude_uses_self_event(
        duplicates_window, globals_event_manager):
    """canvas_image_exclude delegiert mit self.event an canvas_exclude."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])

    events = []
    globals_event_manager.bind("FileStateChanged", lambda e: events.append(e))

    win.event = _FakeMouseEvent(x=5, y=5)
    win.canvas_image_exclude()

    our = [e for e in events if isinstance(e, FileStateEvent)]
    assert len(our) == 1
    assert our[0].filename == info["sources"][0]


def test_on_file_state_changed_updates_duplicate_thumbnail(
        duplicates_window, globals_event_manager):
    """Eingehendes Event fuer das eigene File aktualisiert das Duplikat-Thumbnail."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]

    first = info["sources"][0]
    assert win.dict_thumbnails_duplicates[imagetype][first].getState() == INCLUDE

    globals_event_manager.generate(
        "FileStateChanged", FileStateEvent(first, EXCLUDE))

    assert win.dict_thumbnails_duplicates[imagetype][first].getState() == EXCLUDE


def test_on_file_state_changed_ignores_unknown_file(
        duplicates_window, globals_event_manager):
    """Event fuer ein File, das kein Duplikat ist, wird ignoriert."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]

    before = {p: t.getState()
              for p, t in win.dict_thumbnails_duplicates[imagetype].items()}

    globals_event_manager.generate(
        "FileStateChanged", FileStateEvent("/some/other/file.jpg", EXCLUDE))

    after = {p: t.getState()
             for p, t in win.dict_thumbnails_duplicates[imagetype].items()}
    assert before == after


def test_on_file_state_changed_without_duplicates_is_safe(
        duplicates_window, globals_event_manager):
    """Wenn noch keine Dublette geladen ist, ist das Event ein No-Op."""
    win, caller, info = duplicates_window
    # display_duplicate absichtlich NICHT aufrufen
    assert win.dict_thumbnails_duplicates == {}
    # darf nicht crashen
    globals_event_manager.generate(
        "FileStateChanged", FileStateEvent(info["sources"][0], EXCLUDE))


def test_roundtrip_canvas_exclude_updates_thumbnail_via_event(
        duplicates_window, globals_event_manager):
    """Round-Trip: canvas_exclude feuert Event, on_file_state_changed
    reagiert, der Thumbnail-State ist danach konsistent."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]

    first = info["sources"][0]
    assert win.dict_thumbnails_duplicates[imagetype][first].getState() == INCLUDE

    # Klick auf das erste Thumbnail -> canvas_exclude -> Event ->
    # on_file_state_changed -> setState(EXCLUDE)
    ev = _FakeMouseEvent(x=5, y=5)
    win.canvas_exclude(ev)

    assert win.dict_thumbnails_duplicates[imagetype][first].getState() == EXCLUDE

    # nochmal klicken -> zurueck auf INCLUDE
    win.canvas_exclude(_FakeMouseEvent(x=5, y=5))
    assert win.dict_thumbnails_duplicates[imagetype][first].getState() == INCLUDE
    
# ======================================================================
# Block F: close_handler
# ======================================================================

def test_close_handler_calls_stop_all_players(duplicates_window, monkeypatch):
    """close_handler ruft MyDuplicates.stop_all_players() auf."""
    win, caller, info = duplicates_window
    calls = []
    original = win.stop_all_players
    def spy():
        calls.append(True)
        return original()
    monkeypatch.setattr(win, "stop_all_players", spy)

    win.close_handler()

    assert len(calls) >= 1

def test_close_handler_unbinds_file_state_changed(
        duplicates_window, globals_event_manager):
    """Nach close_handler ist on_file_state_changed nicht mehr registriert."""
    win, caller, info = duplicates_window
    assert win.on_file_state_changed in globals_event_manager.listeners["FileStateChanged"]

    win.close_handler()

    listeners = globals_event_manager.listeners.get("FileStateChanged", [])
    assert win.on_file_state_changed not in listeners


def test_close_handler_unbinds_closing(
        duplicates_window, globals_event_manager):
    """Nach close_handler ist on_closing nicht mehr registriert."""
    win, caller, info = duplicates_window
    assert win.on_closing in globals_event_manager.listeners["Closing"]

    win.close_handler()

    listeners = globals_event_manager.listeners.get("Closing", [])
    assert win.on_closing not in listeners


def test_close_handler_fires_closing_event(
        duplicates_window, globals_event_manager):
    """close_handler feuert ein Closing-Event (mit filename=None)."""
    win, caller, info = duplicates_window
    received = []
    globals_event_manager.bind("Closing", lambda e: received.append(e))

    win.close_handler()

    # mindestens ein Closing-Event mit filename=None und obj=win
    ours = [e for e in received
            if isinstance(e, ClosingEvent) and e.filename is None and e.obj is win]
    assert len(ours) >= 1


def test_close_handler_enables_caller_button(duplicates_window):
    """Nach close_handler ist caller.button_duplicates wieder NORMAL."""
    win, caller, info = duplicates_window
    import tkinter as tk
    # Vorab-Zustand: DISABLED (vom Konstruktor)
    assert str(caller.button_duplicates.cget("state")) == str(tk.DISABLED)

    win.close_handler()

    assert str(caller.button_duplicates.cget("state")) == str(tk.NORMAL)


def test_close_handler_clears_caller_win_duplicates(duplicates_window):
    """Nach close_handler ist caller.win_duplicates None."""
    win, caller, info = duplicates_window
    caller.win_duplicates = win  # simulieren

    win.close_handler()

    assert caller.win_duplicates is None


def test_close_handler_destroys_window(duplicates_window):
    """Nach close_handler existiert das Fenster nicht mehr."""
    win, caller, info = duplicates_window
    win.close_handler()

    assert not win.root.winfo_exists()
    
# ======================================================================
# Block G: stop_all_players
# ======================================================================

def test_stop_all_players_disables_caller_button(duplicates_window):
    """stop_all_players setzt caller.button_duplicates auf DISABLED."""
    win, caller, info = duplicates_window
    import tkinter as tk
    caller.button_duplicates.config(state=tk.NORMAL)

    win.stop_all_players()

    assert str(caller.button_duplicates.cget("state")) == str(tk.DISABLED)


def test_stop_all_players_stops_running_players(duplicates_window_with_players):
    """Player mit getRun()==True bekommen pstop()."""
    win, caller, info, players = duplicates_window_with_players
    running = [p for p in players if p.getRun()]
    assert running, "Fixture muss mindestens einen laufenden Player haben"

    win.stop_all_players()

    for p in running:
        assert p.pstop_calls >= 1


def test_stop_all_players_skips_paused_players(duplicates_window_with_players):
    """Player mit getRun()==False bekommen kein pstop()."""
    win, caller, info, players = duplicates_window_with_players
    paused = [p for p in players if not p.getRun()]
    assert paused, "Fixture muss mindestens einen pausierten Player haben"

    win.stop_all_players()

    for p in paused:
        assert p.pstop_calls == 0


def test_stop_all_players_without_thumbnails_is_safe(duplicates_window):
    """Wenn noch keine Duplikate geladen sind, ist stop_all_players ein No-Op
    (nur caller.button_duplicates wird disabled)."""
    win, caller, info = duplicates_window
    # display_duplicate absichtlich NICHT aufgerufen
    assert win.thumbnails_duplicates == {}

    # darf nicht crashen
    win.stop_all_players()


def test_stop_all_players_unknown_imagetype_is_safe(duplicates_window):
    """Wenn Globals.imagetype nicht in thumbnails_duplicates ist, kein Fehler."""
    win, caller, info = duplicates_window
    import tools
    # imagetype umstellen, sodass er nicht in thumbnails_duplicates steht
    old = tools.Globals.imagetype
    tools.Globals.imagetype = "GIBT_ES_NICHT"
    try:
        # darf nicht crashen
        win.stop_all_players()
    finally:
        tools.Globals.imagetype = old
        
# ======================================================================
# Block H: on_closing (eingehendes Closing-Event)
# ======================================================================

class _FakeFSImage:
    """Minimal-Stand-in fuer ein MyFSImage/MyFSVideo-Objekt in dict_file_image."""
    def __init__(self, filename):
        self.filename = filename


def test_on_closing_removes_own_fs_entry(duplicates_window):
    """Closing-Event mit event.obj == eigener FS-Eintrag entfernt den Eintrag."""
    win, caller, info = duplicates_window
    fake_fs = _FakeFSImage("dummy.jpg")
    win.dict_file_image["dummy.jpg"] = fake_fs

    win.on_closing(ClosingEvent("dummy.jpg", fake_fs))

    assert "dummy.jpg" not in win.dict_file_image


def test_on_closing_keeps_entry_of_other_object(duplicates_window):
    """Closing-Event mit event.obj != gespeichertem Objekt laesst den Eintrag stehen."""
    win, caller, info = duplicates_window
    stored = _FakeFSImage("dummy.jpg")
    other  = _FakeFSImage("dummy.jpg")
    win.dict_file_image["dummy.jpg"] = stored

    win.on_closing(ClosingEvent("dummy.jpg", other))

    assert "dummy.jpg" in win.dict_file_image
    assert win.dict_file_image["dummy.jpg"] is stored


def test_on_closing_unknown_filename_is_safe(duplicates_window):
    """Closing-Event fuer ein File, das nicht in dict_file_image steht, ist ein No-Op."""
    win, caller, info = duplicates_window
    win.on_closing(ClosingEvent("does/not/exist.jpg", _FakeFSImage("does/not/exist.jpg")))
    # keine Exception, dict unveraendert
    assert win.dict_file_image == {}


def test_on_closing_empty_filename(duplicates_window):
    """Closing-Event mit leerem filename (Hauptfenster schliesst sich) ist safe."""
    win, caller, info = duplicates_window
    win.on_closing(ClosingEvent("", win))
    assert win.dict_file_image == {}


def test_on_closing_removes_only_matching_entry(duplicates_window):
    """Bei mehreren Eintraegen wird nur der passende entfernt."""
    win, caller, info = duplicates_window
    fa = _FakeFSImage("a.jpg")
    fb = _FakeFSImage("b.jpg")
    win.dict_file_image["a.jpg"] = fa
    win.dict_file_image["b.jpg"] = fb

    win.on_closing(ClosingEvent("a.jpg", fa))

    assert "a.jpg" not in win.dict_file_image
    assert "b.jpg" in win.dict_file_image
    assert win.dict_file_image["b.jpg"] is fb   

# ======================================================================
# Block I: get_thumbnail_by_position (binaere Suche)
# ======================================================================

def test_get_thumbnail_by_position_start(duplicates_window):
    """Position genau am Start des ersten Thumbnails liefert das erste Thumbnail."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    thumbs = win.thumbnails_duplicates[imagetype]
    first = thumbs[0]
    thumb, idx = win.get_thumbnail_by_position(first.getStart(), 5)
    assert thumb is first
    assert idx == 0


def test_get_thumbnail_by_position_end(duplicates_window):
    """Position genau am End des ersten Thumbnails liefert das erste Thumbnail."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    thumbs = win.thumbnails_duplicates[imagetype]
    first = thumbs[0]
    thumb, idx = win.get_thumbnail_by_position(first.getEnd(), 5)
    assert thumb is first
    assert idx == 0


def test_get_thumbnail_by_position_middle(duplicates_window):
    """Position in der Mitte des ersten Thumbnails liefert das erste Thumbnail."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    thumbs = win.thumbnails_duplicates[imagetype]
    first = thumbs[0]
    mid = (first.getStart() + first.getEnd()) // 2
    thumb, idx = win.get_thumbnail_by_position(mid, 5)
    assert thumb is first
    assert idx == 0


def test_get_thumbnail_by_position_second(duplicates_window):
    """Position mitten im zweiten Thumbnail liefert das zweite Thumbnail."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    thumbs = win.thumbnails_duplicates[imagetype]
    if len(thumbs) < 2:
        pytest.skip("Nur ein Thumbnail vorhanden")
    second = thumbs[1]
    mid = (second.getStart() + second.getEnd()) // 2
    thumb, idx = win.get_thumbnail_by_position(mid, 5)
    assert thumb is second
    assert idx == 1


def test_get_thumbnail_by_position_before_first(duplicates_window):
    """Position vor dem ersten Thumbnail (negativ) liefert None."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    thumb, idx = win.get_thumbnail_by_position(-1000, 5)
    assert thumb is None
    assert idx is None


def test_get_thumbnail_by_position_after_last(duplicates_window):
    """Position weit hinter dem letzten Thumbnail liefert None."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    thumbs = win.thumbnails_duplicates[imagetype]
    last = thumbs[-1]
    thumb, idx = win.get_thumbnail_by_position(last.getEnd() + 10000, 5)
    assert thumb is None
    assert idx is None


def test_get_thumbnail_by_position_empty(duplicates_window):
    """Ohne Thumbnails liefert die Suche None (keine Exception)."""
    win, caller, info = duplicates_window
    # display_duplicate absichtlich NICHT aufrufen
    thumb, idx = win.get_thumbnail_by_position(0, 0)
    assert thumb is None
    assert idx is None


def test_get_thumbnail_by_position_in_gap(duplicates_window):
    """Position in der Luecke zwischen zwei Thumbnails liefert None."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    thumbs = win.thumbnails_duplicates[imagetype]
    if len(thumbs) < 2:
        pytest.skip("Nur ein Thumbnail vorhanden")
    first_end = thumbs[0].getEnd()
    second_start = thumbs[1].getStart()
    # Die Luecke ist normalerweise Globals.gap breit. Wenn sie 0 ist,
    # ueberlappt sie sich, dann kein Testfall.
    if second_start <= first_end:
        pytest.skip("Keine Luecke zwischen den Thumbnails")
    mid_gap = (first_end + second_start) // 2
    thumb, idx = win.get_thumbnail_by_position(mid_gap, 5)
    assert thumb is None
    assert idx is None
 
# ======================================================================
# Block J: canvas_show -> display_image
# ======================================================================

def test_canvas_show_calls_display_image_on_hit(
        duplicates_window, monkeypatch):
    """Klick auf ein Thumbnail ruft display_image mit diesem Thumbnail auf."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    thumbs = win.thumbnails_duplicates[imagetype]
    first = thumbs[0]

    calls = []
    monkeypatch.setattr(win, "display_image", lambda t: calls.append(t))

    # Klick genau in die Mitte des ersten Thumbnails
    mid_x = (first.getStart() + first.getEnd()) // 2
    ev = _FakeMouseEvent(x=mid_x, y=5)
    win.canvas_show(ev)

    assert calls == [first]


def test_canvas_show_no_hit_does_nothing(
        duplicates_window, monkeypatch):
    """Klick ausserhalb jedes Thumbnails ruft display_image nicht auf."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    last = win.thumbnails_duplicates[imagetype][-1]

    calls = []
    monkeypatch.setattr(win, "display_image", lambda t: calls.append(t))

    # weit hinter dem letzten Thumbnail
    ev = _FakeMouseEvent(x=last.getEnd() + 1000, y=5)
    win.canvas_show(ev)

    assert calls == []


def test_canvas_image_show_uses_self_event(
        duplicates_window, monkeypatch):
    """canvas_image_show (Kontextmenue) delegiert mit self.event an canvas_show."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    first = win.thumbnails_duplicates[imagetype][0]

    calls = []
    monkeypatch.setattr(win, "display_image", lambda t: calls.append(t))

    mid_x = (first.getStart() + first.getEnd()) // 2
    win.event = _FakeMouseEvent(x=mid_x, y=5)
    win.canvas_image_show()

    assert calls == [first]


def test_canvas_show_focuses_canvas(duplicates_window, monkeypatch):
    """canvas_show setzt den Fokus auf die Canvas, bevor display_image laeuft."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    imagetype = info["imagetype"]
    first = win.thumbnails_duplicates[imagetype][0]

    focused = []
    original_focus = win.f.focus_set
    monkeypatch.setattr(win.f, "focus_set", lambda: focused.append(True))
    monkeypatch.setattr(win, "display_image", lambda t: None)

    mid_x = (first.getStart() + first.getEnd()) // 2
    win.canvas_show(_FakeMouseEvent(x=mid_x, y=5))

    assert focused == [True]

# ======================================================================
# Block K: resize
# ======================================================================

def test_resize_calls_display_duplicate_on_size_change(
        duplicates_window, monkeypatch):
    """Wenn sich die Fenstergroesse aendert, wird display_duplicate aufgerufen."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    win.thisduplicate = info["target"]

    # Groesse "alt" setzen, sodass resize() eine Aenderung erkennt
    win.width  = 100
    win.height = 100
    monkeypatch.setattr(win.root, "winfo_width",  lambda: 800)
    monkeypatch.setattr(win.root, "winfo_height", lambda: 600)

    calls = []
    monkeypatch.setattr(win, "display_duplicate", lambda t: calls.append(t))

    win.resize()

    assert calls == [info["target"]]


def test_resize_no_size_change_does_not_redraw(
        duplicates_window, monkeypatch):
    """Ohne Aenderung der Fenstergroesse wird display_duplicate nicht aufgerufen."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    win.thisduplicate = info["target"]

    # Groesse "aktuell" setzen, sodass resize() keine Aenderung erkennt
    win.width  = 800
    win.height = 600
    monkeypatch.setattr(win.root, "winfo_width",  lambda: 800)
    monkeypatch.setattr(win.root, "winfo_height", lambda: 600)

    calls = []
    monkeypatch.setattr(win, "display_duplicate", lambda t: calls.append(t))

    win.resize()

    assert calls == []


def test_resize_without_thisduplicate_does_not_redraw(
        duplicates_window, monkeypatch):
    """Ohne ausgewaehlte Dublette wird display_duplicate nicht aufgerufen."""
    win, caller, info = duplicates_window
    # display_duplicate absichtlich NICHT aufrufen -> thisduplicate bleibt None
    assert win.thisduplicate is None

    win.width  = 100
    win.height = 100
    monkeypatch.setattr(win.root, "winfo_width",  lambda: 800)
    monkeypatch.setattr(win.root, "winfo_height", lambda: 600)

    calls = []
    monkeypatch.setattr(win, "display_duplicate", lambda t: calls.append(t))

    win.resize()

    assert calls == []


def test_resize_updates_font_size(duplicates_window, monkeypatch):
    """Bei Groessenaenderung wird die Schriftgroesse neu berechnet."""
    win, caller, info = duplicates_window
    win.width  = 100
    win.height = 100
    monkeypatch.setattr(win.root, "winfo_width",  lambda: 1920)
    monkeypatch.setattr(win.root, "winfo_height", lambda: 1080)

    font_sizes = []
    original_configure = win.text_font.configure
    monkeypatch.setattr(win.text_font, "configure",
                        lambda **kw: font_sizes.append(kw.get("size")))

    win.resize()

    assert len(font_sizes) == 1
    assert font_sizes[0] is not None


def test_resize_updates_width_height(duplicates_window, monkeypatch):
    """Nach resize() sind self.width / self.height auf die neuen Werte gesetzt."""
    win, caller, info = duplicates_window
    win.width  = 100
    win.height = 100
    monkeypatch.setattr(win.root, "winfo_width",  lambda: 1024)
    monkeypatch.setattr(win.root, "winfo_height", lambda: 768)

    win.resize()

    assert win.width  == 1024
    assert win.height == 768 
    
    
# ======================================================================
# Block L: xview (Scrollen)
# ======================================================================

def test_xview_scroll_units_right_moves_canvas(duplicates_window):
    """xview('scroll', 1, 'units') scrollt die Canvas nach rechts."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    win.f.xview('moveto', 0)
    win.f.update()
    before = win.f.canvasx(0)

    win.xview("scroll", 1, "units")
    win.f.update()
    after = win.f.canvasx(0)

    # Bei mehreren Thumbnails sollte sich die Position geaendert haben.
    # Bei nur einem Thumbnail bleibt sie gleich (kein Scroll noetig).
    if len(win.thumbnails_duplicates[info["imagetype"]]) > 1:
        assert after > before


def test_xview_scroll_units_left_at_start_does_nothing(duplicates_window):
    """xview('scroll', -1, 'units') am Anfang scrollt nicht ins Negative."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    win.f.xview('moveto', 0)
    win.f.update()
    before = win.f.xview()

    win.xview("scroll", -1, "units")
    win.f.update()
    after = win.f.xview()

    assert before == after


def test_xview_moveto_start(duplicates_window):
    """xview('moveto', 0) setzt die Position auf den Anfang."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    # erst nach rechts scrollen (falls mehrere Thumbnails)
    win.f.xview('moveto', 1.0)
    win.f.update()

    win.xview("moveto", 0)
    win.f.update()

    # xview() liefert ein Tupel (first, last) der sichtbaren Fraktion.
    # Bei moveto 0 ist first == 0.0.
    first, last = win.f.xview()
    assert first == 0.0
    

def test_xview_no_args_delegates_to_canvas(duplicates_window, monkeypatch):
    """xview() ohne Argumente wird an self.f.xview delegiert (kein Fehler)."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])

    calls = []
    original_xview = win.f.xview
    monkeypatch.setattr(win.f, "xview", lambda *a: calls.append(a))

    # ohne args -> self.f.xview(*args) mit args = ()
    win.xview()

    assert calls == [()]


def test_xview_scroll_units_at_end_does_not_crash(duplicates_window):
    """xview('scroll', 1, 'units') am rechten Rand wirft keinen Fehler."""
    win, caller, info = duplicates_window
    win.display_duplicate(info["target"])
    win.f.xview('moveto', 1.0)
    win.f.update()

    # sollte einfach nichts tun, nicht crashen
    win.xview("scroll", 1, "units")
    win.f.update()

    