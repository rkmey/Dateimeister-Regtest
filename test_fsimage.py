# -*- coding: utf-8 -*-
"""
Regressionstests fuer MyFSImage (Dateimeister_FSimage.py).

MyFSImage ist das Detailfenster fuer STILL- und RAW-Bilder. Es zeigt
ein Bild und bietet Buttons fuer "Fit Canvas", "Full scale", "Print",
"Include/Exclude", optional "raw full" und "Fullscreen".

Getestet werden:
  * Konstruktion, Event-Registrierung, Bild-Laden (STILL und RAW)
  * print_handler (STILL direkt, RAW embedded, RAW full)
  * on_button_state feuert FileStateEvent mit getoggtem State
  * on_file_state_changed reagiert nur auf das eigene File
  * on_closing schliesst nur bei passendem caller
  * close_handler feuert ClosingEvent und zerstoert das Fenster
  * Fullscreen (Flag, Frame-Eltern, Escape-Binding, Timer-Abbruch)
  * RAW-Toggle (embedded <-> full, Fehlerfall, ignoriert STILL)
  * _close_images schliesst alle Bilder
  * USE_JPEG-Fallback auf RAW (mit und ohne Erfolg)

Nicht getestet:
  * die tatsaechliche Bilddarstellung auf dem Canvas
  * die Zoom-Logik (image_zoom / mousewheel)
  * die Auto-Hide-Overlay-Logik im Detail
  * die Mouse-Watch-Logik im Detail
  * der echte rawpy-Zugriff (dafuer gibt es fake_rawpy_loader)
"""

import os

import pytest

from tools import INCLUDE, EXCLUDE, FileStateEvent, ClosingEvent, PrintRequestEvent


# ----------------------------------------------------------------------
# Hilfsfunktionen
# ----------------------------------------------------------------------

def make_fsimage(thumbnail, caller=None, debug=False):
    """Erzeugt ein MyFSImage mit den noetigen Standardtexten."""
    import Dateimeister_FSimage as FS
    return FS.MyFSImage(
        file=thumbnail.getFile(),
        thumbnail=thumbnail,
        caller=caller,
        str_title_prefix="Test: ",
        str_include="Include",
        str_exclude="Exclude",
        str_included="Included",
        str_excluded="Excluded",
        debug=debug,
    )


# ======================================================================
# 1. Konstruktion
# ======================================================================

def test_constructor_registers_events(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """MyFSImage registriert sich fuer FileStateChanged und Closing."""
    fs = make_fsimage(mini_thumbnail)
    try:
        listeners = globals_event_manager.listeners
        assert "FileStateChanged" in listeners
        assert fs.on_file_state_changed in listeners["FileStateChanged"]
        assert "Closing" in listeners
        assert fs.on_closing in listeners["Closing"]
    finally:
        fs.close_handler()


def test_constructor_reads_image(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Der Konstruktor laedt das Bild und legt es auf den Canvas."""
    fs = make_fsimage(mini_thumbnail)
    try:
        assert fs.image is not None
        assert fs.image.size == (64, 48)
    finally:
        fs.close_handler()


def test_constructor_creates_button_and_label(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Button_exclude und Label_status existieren mit passenden Texten."""
    fs = make_fsimage(mini_thumbnail)
    try:
        assert fs.Button_exclude is not None
        assert fs.Label_status is not None
        assert fs.Button_exclude.cget("text") == "Exclude"
        assert fs.Label_status.cget("text") == "Included"
    finally:
        fs.close_handler()


def test_constructor_still_has_no_raw_button(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Fuer STILL darf der RAW-Button nicht existieren."""
    fs = make_fsimage(mini_thumbnail)
    try:
        assert not hasattr(fs, "Button_raw")
    finally:
        fs.close_handler()


def test_constructor_raw_uses_embedded(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager):
    """Bei RAW wird im Konstruktor load_raw_embedded benutzt."""
    fs = make_fsimage(raw_thumbnail)
    try:
        assert fs.image is not None
        assert fs.raw_mode == "embedded"
        assert fs.image_embedded is not None
        assert fs.image_full is None
        assert len(fake_rawpy_loader.embedded_calls) == 1
        assert fake_rawpy_loader.embedded_calls[0] == raw_thumbnail.getFile()
    finally:
        fs.close_handler()


def test_constructor_raw_creates_raw_button_and_label(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager):
    """Bei RAW existieren Button_raw und Label_rawinfo."""
    fs = make_fsimage(raw_thumbnail)
    try:
        assert hasattr(fs, "Button_raw")
        assert hasattr(fs, "Label_rawinfo")
        assert fs.Button_raw.cget("text") == "raw full"
        assert fs.Label_rawinfo.cget("text") == "RAW using embedded"
    finally:
        fs.close_handler()


def test_constructor_raises_without_thumbnail(
        tk_root, globals_event_manager):
    """Ohne Thumbnail wirft MyFSImage einen RuntimeError."""
    import Dateimeister_FSimage as FS
    with pytest.raises(RuntimeError):
        FS.MyFSImage(
            file=None,
            thumbnail=None,
            caller=None,
            str_title_prefix="Test: ",
            str_include="Include",
            str_exclude="Exclude",
            str_included="Included",
            str_excluded="Excluded",
            debug=False,
        )


def test_constructor_with_minimal_thumbnail_opens_as_still(
        tk_root, test_image, mini_thumbnail_no_imagetype, globals_event_manager):
    """Ein Thumbnail ohne process_type wird als STILL geoeffnet
    (weder RAW noch VIDEO noch USE_JPEG)."""
    fs = make_fsimage(mini_thumbnail_no_imagetype)
    try:
        assert fs.is_raw is False
        assert fs.image is not None
    finally:
        fs.close_handler()


def test_use_jpeg_without_companion_loads_raw(
        tk_root, raw_thumbnail_use_jpeg, fake_rawpy_loader,
        globals_event_manager):
    """Bei process_type=USE_JPEG und fehlendem Begleit-JPEG faellt
    MyFSImage auf den RAW-Loader zurueck und schaltet in den RAW-Modus.
    """
    fs = make_fsimage(raw_thumbnail_use_jpeg)
    try:
        assert len(fake_rawpy_loader.embedded_calls) == 1
        assert fake_rawpy_loader.embedded_calls[0] == raw_thumbnail_use_jpeg.getFile()
        assert fs.is_raw is True
        assert fs.raw_mode == "embedded"
        assert hasattr(fs, "Button_raw")
        assert hasattr(fs, "Label_rawinfo")
        assert fs.Button_raw.cget("text") == "raw full"
        assert fs.Label_rawinfo.cget("text") == "RAW using embedded"
    finally:
        fs.close_handler()


def test_use_jpeg_without_companion_warns_when_raw_fails(
        tk_root, raw_thumbnail_use_jpeg, fake_rawpy_loader_no_embedded,
        globals_event_manager, _global_info_box_mock):
    """Wenn der RAW-Loader den USE_JPEG-Fallback auch nicht oeffnen
    kann, kommt eine Warnung, und das FSImage-Fenster oeffnet sich nicht.
    """
    with pytest.raises(RuntimeError):
        make_fsimage(raw_thumbnail_use_jpeg)
    assert len(_global_info_box_mock) >= 1
    levels = [level for _, level in _global_info_box_mock]
    assert "warnung" in levels, f"Keine Warnung gefeuert: {levels}"


# ======================================================================
# 2. print_handler
# ======================================================================

def test_print_handler_still_fires_print_request_event(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Bei STILL wird die Originaldatei im Event uebergeben."""
    fs = make_fsimage(mini_thumbnail)
    try:
        events = []
        globals_event_manager.bind("PrintRequestEvent", lambda e: events.append(e))

        fs.print_handler()

        assert len(events) == 1
        e = events[0]
        assert isinstance(e, PrintRequestEvent)
        assert e.filename == test_image
        assert e.source is fs
    finally:
        fs.close_handler()


def test_print_handler_raw_embedded_creates_png(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager,
        globals_datadir):
    """Bei RAW im embedded-Modus wird das embedded-Bild als PNG gespeichert.
    load_raw_full darf NICHT aufgerufen werden."""
    fs = make_fsimage(raw_thumbnail)
    try:
        assert fs.raw_mode == "embedded"
        assert len(fake_rawpy_loader.full_calls) == 0

        events = []
        globals_event_manager.bind("PrintRequestEvent", lambda e: events.append(e))

        fs.print_handler()

        # Kein Nachladen
        assert len(fake_rawpy_loader.full_calls) == 0
        # Event gefeuert
        assert len(events) == 1
        e = events[0]
        assert e.filename.endswith(".png")
        assert os.path.isfile(e.filename)
        assert e.source is fs
    finally:
        fs.close_handler()


def test_print_handler_raw_full_creates_png(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager,
        globals_datadir):
    """Bei RAW im full-Modus wird das volle Bild als PNG gespeichert."""
    fs = make_fsimage(raw_thumbnail)
    try:
        # Auf full umschalten
        fs.on_button_raw()
        assert fs.raw_mode == "full"
        assert len(fake_rawpy_loader.full_calls) == 1

        events = []
        globals_event_manager.bind("PrintRequestEvent", lambda e: events.append(e))

        fs.print_handler()

        # Kein weiterer load-Aufruf
        assert len(fake_rawpy_loader.full_calls) == 1
        # Event gefeuert
        assert len(events) == 1
        e = events[0]
        assert e.filename.endswith(".png")
        assert os.path.isfile(e.filename)
    finally:
        fs.close_handler()


# ======================================================================
# 3. on_button_state (Include <-> Exclude)
# ======================================================================

def test_on_button_state_fires_file_state_event_include_to_exclude(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Von INCLUDE nach EXCLUDE: Event mit state=EXCLUDE."""
    fs = make_fsimage(mini_thumbnail)
    try:
        assert mini_thumbnail.getState() == INCLUDE
        events = []
        globals_event_manager.bind("FileStateChanged", lambda e: events.append(e))

        fs.on_button_state()

        our = [e for e in events if isinstance(e, FileStateEvent)]
        assert len(our) == 1
        assert our[0].filename == test_image
        assert our[0].state == EXCLUDE
    finally:
        fs.close_handler()


def test_on_button_state_fires_file_state_event_exclude_to_include(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Von EXCLUDE nach INCLUDE: Event mit state=INCLUDE."""
    mini_thumbnail.setState(EXCLUDE)
    fs = make_fsimage(mini_thumbnail)
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
# 4. on_file_state_changed (eingehende Events)
# ======================================================================

def test_on_file_state_changed_updates_button_and_label(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Eingehendes FileStateChanged fuer das eigene File aktualisiert
    Button-Text, Label und Thumbnail-State."""
    fs = make_fsimage(mini_thumbnail)
    try:
        globals_event_manager.generate(
            "FileStateChanged",
            FileStateEvent(test_image, EXCLUDE),
        )
        assert fs.Button_exclude.cget("text") == "Include"
        assert fs.Label_status.cget("text") == "Excluded"
        assert mini_thumbnail.getState() == EXCLUDE
    finally:
        fs.close_handler()


def test_on_file_state_changed_ignores_other_file(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Ein eingehendes FileStateChanged fuer ein anderes File wird ignoriert."""
    fs = make_fsimage(mini_thumbnail)
    try:
        state_before = mini_thumbnail.getState()
        globals_event_manager.generate(
            "FileStateChanged",
            FileStateEvent("/some/other/file.jpg", EXCLUDE),
        )
        assert mini_thumbnail.getState() == state_before
        assert fs.Button_exclude.cget("text") == "Exclude"
    finally:
        fs.close_handler()


# ======================================================================
# 5. on_closing
# ======================================================================

def test_on_closing_closes_when_caller_matches(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Wenn event.obj der caller ist, schliesst sich das Fenster."""
    caller = object()
    fs = make_fsimage(mini_thumbnail, caller=caller)
    root_ref = fs.root

    fs.on_closing(ClosingEvent("", caller))

    try:
        exists = root_ref.winfo_exists()
    except Exception:
        exists = 0
    assert not exists


def test_on_closing_ignores_other_caller(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Wenn event.obj nicht der caller ist, bleibt das Fenster offen."""
    caller = object()
    other = object()
    fs = make_fsimage(mini_thumbnail, caller=caller)
    try:
        fs.on_closing(ClosingEvent("", other))
        assert fs.root.winfo_exists()
    finally:
        fs.close_handler()


# ======================================================================
# 6. close_handler
# ======================================================================

def test_close_handler_fires_closing_event(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """close_handler feuert ClosingEvent mit file und self."""
    fs = make_fsimage(mini_thumbnail)
    events = []
    globals_event_manager.bind("Closing", lambda e: events.append(e))

    fs.close_handler()

    our = [e for e in events if isinstance(e, ClosingEvent)]
    assert len(our) == 1
    assert our[0].filename == test_image
    assert our[0].obj is fs


def test_close_handler_unbinds_events(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Nach close_handler darf MyFSImage nicht mehr in den Listenern stehen."""
    fs = make_fsimage(mini_thumbnail)
    fs.close_handler()

    listeners = globals_event_manager.listeners
    if "FileStateChanged" in listeners:
        assert fs.on_file_state_changed not in listeners["FileStateChanged"]
    if "Closing" in listeners:
        assert fs.on_closing not in listeners["Closing"]


def test_close_handler_destroys_window(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """Nach close_handler existiert das Tk-Fenster nicht mehr."""
    fs = make_fsimage(mini_thumbnail)
    root_ref = fs.root

    fs.close_handler()

    try:
        exists = root_ref.winfo_exists()
    except Exception:
        exists = 0
    assert not exists


# ======================================================================
# 7. Fullscreen
# ======================================================================

def test_toggle_fullscreen_sets_flag(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """toggle_fullscreen setzt is_fullscreen, macht den Canvas zum
    Vollflaeche-Widget und verschiebt die Kontrollframes als Overlay
    in den Canvas.
    """
    fs = make_fsimage(mini_thumbnail)
    try:
        assert fs.is_fullscreen is False
        fs.toggle_fullscreen()
        assert fs.is_fullscreen is True
        fs.root.update_idletasks()

        # Der Canvas fuellt jetzt das gesamte Fenster.
        info = fs.frame_canvas.place_info()
        assert float(info["relwidth"]) == 1.0
        assert float(info["relheight"]) == 1.0

        # Die beiden Kontrollframes sind jetzt Overlays im Canvas.
        info_1_1 = fs.frame_1_1.place_info()
        info_1_2 = fs.frame_1_2.place_info()
        assert info_1_1.get("in") == fs.frame_canvas
        assert info_1_2.get("in") == fs.frame_canvas
    finally:
        fs.close_handler()


def test_exit_fullscreen_restores_layout(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """exit_fullscreen bringt die Frames zurueck ins Root-Fenster."""
    fs = make_fsimage(mini_thumbnail)
    try:
        fs.toggle_fullscreen()
        fs.exit_fullscreen()
        assert fs.is_fullscreen is False
        fs.root.update_idletasks()

        for frame in (fs.frame_1_1, fs.frame_1_2, fs.frame_2):
            info = frame.place_info()
            assert info.get("in") == fs.root
    finally:
        fs.close_handler()


def test_escape_binding_active_in_fullscreen(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """In Fullscreen ist <Escape> an exit_fullscreen gebunden."""
    fs = make_fsimage(mini_thumbnail)
    try:
        fs.toggle_fullscreen()
        bindings = fs.root.bind("<Escape>")
        assert bindings, "Escape ist nicht gebunden"
    finally:
        fs.close_handler()


def test_close_handler_cancels_fullscreen_timers(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """close_handler bricht Fullscreen-Timer ab."""
    fs = make_fsimage(mini_thumbnail)
    try:
        fs.toggle_fullscreen()
        assert fs._hide_timer_id is not None or fs._mouse_watch_id is not None
    finally:
        fs.close_handler()
    assert fs._hide_timer_id is None
    assert fs._mouse_watch_id is None


# ======================================================================
# 8. RAW-Toggle
# ======================================================================

def test_on_button_raw_loads_full(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager):
    """Erster Klick auf raw full laedt das volle Bild."""
    fs = make_fsimage(raw_thumbnail)
    try:
        assert fs.raw_mode == "embedded"
        assert fs.image_full is None
        assert len(fake_rawpy_loader.full_calls) == 0

        fs.on_button_raw()

        assert fs.raw_mode == "full"
        assert fs.image_full is not None
        assert len(fake_rawpy_loader.full_calls) == 1
        assert fs.Button_raw.cget("text") == "Use embedded"
        assert fs.Label_rawinfo.cget("text") == "RAW using FULL"
    finally:
        fs.close_handler()


def test_on_button_raw_toggles_back_to_embedded(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager):
    """Zweiter Klick wechselt zurueck zu embedded (ohne erneutes Laden)."""
    fs = make_fsimage(raw_thumbnail)
    try:
        fs.on_button_raw()
        assert fs.raw_mode == "full"
        assert len(fake_rawpy_loader.full_calls) == 1

        fs.on_button_raw()
        assert fs.raw_mode == "embedded"
        assert len(fake_rawpy_loader.full_calls) == 1
        assert fs.Button_raw.cget("text") == "raw full"
        assert fs.Label_rawinfo.cget("text") == "RAW using embedded"
    finally:
        fs.close_handler()


def test_on_button_raw_reuses_cached_full(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager):
    """Bei mehrfachem Hin- und Herschalten wird full nur einmal geladen."""
    fs = make_fsimage(raw_thumbnail)
    try:
        fs.on_button_raw()  # -> full
        fs.on_button_raw()  # -> embedded
        fs.on_button_raw()  # -> full (cache)
        assert fs.raw_mode == "full"
        assert len(fake_rawpy_loader.full_calls) == 1
    finally:
        fs.close_handler()


def test_on_button_raw_handles_load_error(
        tk_root, raw_thumbnail, fake_rawpy_loader_failing,
        globals_event_manager, _global_info_box_mock):
    """Wenn load_raw_full fehlschlaegt, bleibt der Modus auf embedded."""
    fs = make_fsimage(raw_thumbnail)
    try:
        assert fs.raw_mode == "embedded"

        fs.on_button_raw()

        assert fs.raw_mode == "embedded"
        assert fs.image_full is None
        assert len(_global_info_box_mock) >= 1
        assert fs.Button_raw.cget("text") == "raw full"
    finally:
        fs.close_handler()


def test_on_button_raw_ignores_for_still(
        tk_root, test_image, mini_thumbnail, globals_event_manager):
    """on_button_raw tut nichts, wenn das Bild kein RAW ist."""
    fs = make_fsimage(mini_thumbnail)
    try:
        if hasattr(fs, "on_button_raw"):
            fs.on_button_raw()
        assert fs.is_raw is False
    finally:
        fs.close_handler()


def test_on_button_raw_shows_status_labels(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager):
    """Die Status-Labels wechseln korrekt zwischen embedded und full."""
    fs = make_fsimage(raw_thumbnail)
    try:
        assert fs.Label_rawinfo.cget("text") == "RAW using embedded"

        fs.on_button_raw()
        assert fs.Label_rawinfo.cget("text") == "RAW using FULL"

        fs.on_button_raw()
        assert fs.Label_rawinfo.cget("text") == "RAW using embedded"
    finally:
        fs.close_handler()


# ======================================================================
# 9. Metadata und _close_images
# ======================================================================

def test_read_all_metadata_raw_merges_sources(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager):
    """Bei RAW kombiniert _read_all_metadata die zwei Loader-Aufrufe."""
    fs = make_fsimage(raw_thumbnail)
    try:
        result = fs._read_all_metadata()
        assert "RAW" in result
        assert "EXIF" in result
        assert len(fake_rawpy_loader.metadata_calls) == 1
        assert len(fake_rawpy_loader.all_exif_calls) == 1
    finally:
        fs.close_handler()


def test_close_images_closes_all(
        tk_root, raw_thumbnail, fake_rawpy_loader, globals_event_manager):
    """_close_images schliesst image_embedded und image_full."""
    fs = make_fsimage(raw_thumbnail)
    fs.on_button_raw()
    assert fs.image_embedded is not None
    assert fs.image_full is not None

    fs._close_images()

    assert fs.image_embedded is None
    assert fs.image_full is None
    assert fs.image is None

    fs.close_handler()