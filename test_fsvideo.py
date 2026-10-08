# -*- coding: utf-8 -*-
"""
Regressionstests fuer MyFSVideo (Dateimeister_FSVideo.py).

MyFSVideo ist das Detailfenster fuer VIDEODATEIEN. Es steuert mpv,
zeigt Metadaten und bietet Include/Exclude und Print.

Getestet werden:
  * Konstruktion und Event-Registrierung
  * on_button_state feuert FileStateEvent mit getoggtem State
  * on_file_state_changed reagiert nur auf das eigene File
  * on_closing schliesst nur bei passendem caller
  * close_handler feuert ClosingEvent und zerstört das Fenster
  * Metadata-Population und on_button_all_meta
  * print_frame feuert PrintRequestEvent

Nicht getestet (bewusst, siehe Landkarte):
  * Video-Player-Steuerung (Play, Pause, Seek, Frame-Step, Vollbild)
  * Position-Polling und Zeitleisten-Vorschau
  * Frame-Step-Hold-Mechanik
  * Fokus-Handling
  * _read_all_metadata (hängt von ffprobe ab)

Voraussetzungen: fake_mpv, video_thumbnail, globals_event_manager, tk_root.
"""

import pytest

from tools import INCLUDE, EXCLUDE, FileStateEvent, ClosingEvent, PrintRequestEvent


# ----------------------------------------------------------------------
# Hilfsfunktionen
# ----------------------------------------------------------------------

def make_fsvideo(thumbnail, caller=None, debug=False, temp_dir=None):
    """Erzeugt ein MyFSVideo mit den noetigen Standardtexten."""
    import Dateimeister_FSVideo as FSV
    import tools
    return FSV.MyFSVideo(
        file=thumbnail.getFile(),
        thumbnail=thumbnail,
        caller=caller,
        str_title_prefix="Test: ",
        str_include="Include",
        str_exclude="Exclude",
        str_included="Included",
        str_excluded="Excluded",
        temp_dir=temp_dir or tools.Globals.datadir,
        num_thumbnails=5,
        mpv_path="/fake/mpv",
        ffprobe_path="/fake/ffprobe",
        debug=debug,
    )


# ======================================================================
# 1. Konstruktion und Event-Registrierung
# ======================================================================

def test_constructor_registers_events(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """MyFSVideo registriert sich fuer FileStateChanged und Closing."""
    fs = make_fsvideo(video_thumbnail)
    try:
        listeners = globals_event_manager.listeners
        assert "FileStateChanged" in listeners
        assert fs.on_file_state_changed in listeners["FileStateChanged"]
        assert "Closing" in listeners
        assert fs.on_closing in listeners["Closing"]
    finally:
        fs.close_handler()


def test_constructor_creates_metadata_treeview(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Nach dem Konstruktor existiert ein Treeview mit den richtigen Spalten."""
    fs = make_fsvideo(video_thumbnail)
    try:
        assert fs.tv is not None
        assert fs.tv.cget("columns")  # Spalten konfiguriert
    finally:
        fs.close_handler()


def test_constructor_initial_metadata_populated(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Der Treeview ist mit den Metadaten aus dem Thumbnail befuellt."""
    fs = make_fsvideo(video_thumbnail)
    try:
        items = fs.tv.get_children("")
        assert len(items) > 0, "Metadata-Treeview ist leer"
    finally:
        fs.close_handler()


# ======================================================================
# 2. on_button_state (Include <-> Exclude)
# ======================================================================

def test_on_button_state_fires_file_state_event_include_to_exclude(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Von INCLUDE nach EXCLUDE: Event mit state=EXCLUDE."""
    fs = make_fsvideo(video_thumbnail)
    try:
        assert video_thumbnail.getState() == INCLUDE
        events = []
        globals_event_manager.bind("FileStateChanged", lambda e: events.append(e))

        fs.on_button_state()

        our = [e for e in events if isinstance(e, FileStateEvent)]
        assert len(our) == 1
        assert our[0].state == EXCLUDE
        assert our[0].filename == video_thumbnail.getFile()
    finally:
        fs.close_handler()


def test_on_button_state_fires_file_state_event_exclude_to_include(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Von EXCLUDE nach INCLUDE: Event mit state=INCLUDE."""
    video_thumbnail.setState(EXCLUDE)
    fs = make_fsvideo(video_thumbnail)
    try:
        events = []
        globals_event_manager.bind("FileStateChanged", lambda e: events.append(e))

        fs.on_button_state()

        our = [e for e in events if isinstance(e, FileStateEvent)]
        assert len(our) == 1
        assert our[0].state == INCLUDE
    finally:
        fs.close_handler()


# ======================================================================
# 3. on_file_state_changed (eingehende Events)
# ======================================================================

def test_on_file_state_changed_updates_button_and_label(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Ein eingehendes FileStateChanged fuer das eigene File aktualisiert
    Button-Text, Label und Thumbnail-State."""
    fs = make_fsvideo(video_thumbnail)
    try:
        globals_event_manager.generate(
            "FileStateChanged",
            FileStateEvent(video_thumbnail.getFile(), EXCLUDE),
        )
        assert video_thumbnail.getState() == EXCLUDE
        # Button-Text sollte jetzt auf "Include" stehen (weil EXCLUDE aktiv)
        assert fs.btn_inex.cget("text") == "Include"
        assert fs.lbl_inex.cget("text") == "Excluded"
    finally:
        fs.close_handler()


def test_on_file_state_changed_ignores_other_file(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Ein eingehendes FileStateChanged fuer ein anderes File wird ignoriert."""
    fs = make_fsvideo(video_thumbnail)
    try:
        state_before = video_thumbnail.getState()
        globals_event_manager.generate(
            "FileStateChanged",
            FileStateEvent("/some/other/file.mp4", EXCLUDE),
        )
        assert video_thumbnail.getState() == state_before
    finally:
        fs.close_handler()


# ======================================================================
# 4. on_closing
# ======================================================================

def test_on_closing_closes_when_caller_matches(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Wenn event.obj der caller ist, schliesst sich das Fenster."""
    caller = object()
    fs = make_fsvideo(video_thumbnail, caller=caller)
    root_ref = fs.root

    fs.on_closing(ClosingEvent("", caller))

    try:
        exists = root_ref.winfo_exists()
    except Exception:
        exists = 0
    assert not exists


def test_on_closing_ignores_other_caller(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Wenn event.obj nicht der caller ist, bleibt das Fenster offen."""
    caller = object()
    other = object()
    fs = make_fsvideo(video_thumbnail, caller=caller)
    try:
        fs.on_closing(ClosingEvent("", other))
        assert fs.root.winfo_exists()
    finally:
        fs.close_handler()


# ======================================================================
# 5. close_handler
# ======================================================================

def test_close_handler_fires_closing_event(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """close_handler feuert ClosingEvent mit file und self."""
    fs = make_fsvideo(video_thumbnail)
    events = []
    globals_event_manager.bind("Closing", lambda e: events.append(e))

    fs.close_handler()

    our = [e for e in events if isinstance(e, ClosingEvent)]
    assert len(our) == 1
    assert our[0].filename == video_thumbnail.getFile()
    assert our[0].obj is fs


def test_close_handler_unbinds_events(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Nach close_handler steht MyFSVideo nicht mehr in den Listenern."""
    fs = make_fsvideo(video_thumbnail)
    fs.close_handler()

    listeners = globals_event_manager.listeners
    if "FileStateChanged" in listeners:
        assert fs.on_file_state_changed not in listeners["FileStateChanged"]
    if "Closing" in listeners:
        assert fs.on_closing not in listeners["Closing"]


def test_close_handler_destroys_window(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """Nach close_handler existiert das Tk-Fenster nicht mehr."""
    fs = make_fsvideo(video_thumbnail)
    root_ref = fs.root

    fs.close_handler()

    try:
        exists = root_ref.winfo_exists()
    except Exception:
        exists = 0
    assert not exists


def test_close_handler_stops_polling(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """close_handler setzt _stop_polling auf True."""
    fs = make_fsvideo(video_thumbnail)
    assert fs._stop_polling is False
    fs.close_handler()
    assert fs._stop_polling is True


# ======================================================================
# 6. Metadata
# ======================================================================

def test_populate_metadata_tree_with_selected_metadata(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """_populate_metadata_tree fuellt den Treeview aus thumbnail.metadata."""
    fs = make_fsvideo(video_thumbnail)
    try:
        items = fs.tv.get_children("")
        assert len(items) > 0
        # Die erste Zeile sollte eine Kategorie aus den Metadaten zeigen
        first = items[0]
        assert fs.tv.item(first, "text") != ""  # Kategorie-Spalte gefuellt
    finally:
        fs.close_handler()


def test_populate_metadata_tree_with_empty_metadata(
        tk_root, fake_mpv, video_thumbnail_empty_metadata, globals_event_manager,
        globals_screen, globals_datadir):
    """Bei leeren Metadaten erscheint ein Hinweis-Eintrag."""
    fs = make_fsvideo(video_thumbnail_empty_metadata)
    try:
        items = fs.tv.get_children("")
        assert len(items) == 1
        values = fs.tv.item(items[0], "values")
        assert any("no metadata" in str(v).lower() for v in values)
    finally:
        fs.close_handler()

def test_on_button_all_meta_toggles(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """on_button_all_meta wechselt zwischen selected und all."""
    fs = make_fsvideo(video_thumbnail)
    try:
        assert fs.show_all_meta is False
        fs.on_button_all_meta()
        assert fs.show_all_meta is True
        fs.on_button_all_meta()
        assert fs.show_all_meta is False
    finally:
        fs.close_handler()


# ======================================================================
# 7. print_frame
# ======================================================================

def test_print_frame_fires_print_request_event(
        tk_root, fake_mpv, video_thumbnail, globals_event_manager,
        globals_screen, globals_datadir):
    """print_frame erzeugt einen Screenshot und feuert PrintRequestEvent."""
    import Dateimeister_FSVideo as FSV
    fs = make_fsvideo(video_thumbnail)
    try:
        # mpv_ipc manuell setzen (normalerweise per IPC-Thread verbunden)
        fs.mpv_ipc = fake_mpv()
        fs.is_paused = True

        events = []
        globals_event_manager.bind("PrintRequestEvent", lambda e: events.append(e))

        fs.print_frame()

        our = [e for e in events if isinstance(e, PrintRequestEvent)]
        assert len(our) == 1
        e = our[0]
        # Der Pfad ist der Screenshot, nicht das Video
        assert e.filename.endswith(".png")
        assert "print_frame_" in e.filename
        assert e.source is fs
    finally:
        fs.close_handler()