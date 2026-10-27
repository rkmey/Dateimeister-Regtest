# -*- coding: utf-8 -*-
"""
Regressionstests für den Kamera-Dialog (MyCameraTreeview).

Aufgeteilt in einzelne, klar benannte Tests, damit ein roter Test
sofort sagt, welche Aktion nicht funktioniert.

Alle Tests laufen unbeaufsichtigt:
  * messagebox und tools.info_box werden global in conftest.py gemockt
  * pytest-timeout bricht hängende Tests nach 60 s ab
  * nach jedem Test wird geprüft, ob Toplevel-Fenster offen sind
"""

import pytest


# ----------------------------------------------------------------------
# Hilfsfunktionen
# ----------------------------------------------------------------------

def make_camera_window(dummy_main, proctypes="jpeg,use_jpeg,video", debug=False,
                       cameraname="DIATISCH"):
    from Dateimeister_camera import MyCameraTreeview
    return MyCameraTreeview(pmain=dummy_main, proctypes=proctypes,
                            debug=debug, cameraname=cameraname)

def find_iid_by_text(tv, text, tag=None):
    for iid in tv.get_children(""):
        if tv.item(iid, "text") == text and (tag is None or tag in tv.item(iid, "tag")):
            return iid
    return None


def find_child_iid_by_text(tv, parent_iid, text, tag=None):
    for iid in tv.get_children(parent_iid):
        if tv.item(iid, "text") == text and (tag is None or tag in tv.item(iid, "tag")):
            return iid
    return None


def _make_fake_event():
    class FakeEvent:
        x = y = 0
        x_root = y_root = 0
    return FakeEvent()


# ======================================================================
# 1. Baum-Aufbau
# ======================================================================

def test_treeview_from_xml_builds_hierarchy(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """Prüft, dass treeview_from_xml() die Kamera-Hierarchie aufbaut.

    Die Spalten sind col_modified, col_subdir, col_process (kein
    col_rendertype mehr).
    """
    win = make_camera_window(dummy_main)
    try:
        tv = win.tv
        iid_dia = find_iid_by_text(tv, "DIATISCH", tag="camera")
        assert iid_dia is not None, "DIATISCH-Kamera fehlt"
        iid_jpeg = find_child_iid_by_text(tv, iid_dia, "JPEG", tag="type")
        assert iid_jpeg is not None, "DIATISCH/JPEG fehlt"
        assert tv.item(iid_jpeg, "values")[1] == "Diatisch"
        iid_jpg = find_child_iid_by_text(tv, iid_jpeg, "JPG", tag="suffix")
        assert iid_jpg is not None, "DIATISCH/JPEG/JPG fehlt"
        assert tv.item(iid_jpg, "values")[2] == "JPEG"
    finally:
        win.close_handler()


def test_treeview_from_xml_prompts_for_missing_process_image(
        tk_root, tmp_xml_incomplete, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips,
        silence_messageboxes):
    """Bei fehlendem process_image muss ein Forced Dialog erscheinen."""
    win = make_camera_window(dummy_main, cameraname="TESTCAM")
    try:
        info_calls = [c for c in silence_messageboxes if c[0] == "info"]
        assert info_calls, "Kein showinfo-Aufruf für fehlendes process_image"
        msgs = " | ".join(str(c[1]) for c in info_calls)
        assert "process_image" in msgs, f"Hinweis fehlt: {msgs}"
        assert win.newitem == "PROCESS_IMAGE"
        assert win.tag == "suffix"
    finally:
        win.close_handler()


# ======================================================================
# 2. Kamera-Aktionen
# ======================================================================

def test_apply_new_camera_new(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """CAMERA_NEW: Kamera + Type + Suffix werden angelegt."""
    win = make_camera_window(dummy_main)
    try:
        win.camera_new()
        win.new_text(win.entry_camera, "NEWCAM")
        win.new_text(win.entry_type, "JPEG")
        win.new_text(win.entry_suffix, "JPG")
        win.apply_new()

        import dateimeister_config_xml as DX
        result = DX.get_cameras_types_suffixes(tmp_xml)
        assert "NEWCAM" in result
        assert "JPEG" in result["NEWCAM"]
        assert "JPG" in result["NEWCAM"]["JPEG"]
    finally:
        win.close_handler()


def test_apply_new_camera_rename(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """CAMERA_RENAME: Kamera wird umbenannt, Type bleibt erhalten."""
    win = make_camera_window(dummy_main)
    try:
        iid = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        win.item = iid
        win.text = "DIATISCH"
        win.tag = "camera"
        win.camera = "DIATISCH"
        win.camera_change()
        win.new_text(win.entry_camera, "RENAMED")
        win.apply_new()

        import dateimeister_config_xml as DX
        result = DX.get_cameras_types_suffixes(tmp_xml)
        assert "RENAMED" in result
        assert "DIATISCH" not in result
        assert "JPEG" in result["RENAMED"]
    finally:
        win.close_handler()


def test_apply_new_camera_delete(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """CAMERA_DELETE: Kamera wird komplett entfernt."""
    win = make_camera_window(dummy_main)
    try:
        iid = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        win.item = iid
        win.text = "DIATISCH"
        win.tag = "camera"
        win.camera = "DIATISCH"
        win.camera_delete()

        import dateimeister_config_xml as DX
        result = DX.get_cameras_types_suffixes(tmp_xml)
        assert "DIATISCH" not in result
    finally:
        win.close_handler()


# ======================================================================
# 3. Type-Aktionen
# ======================================================================

def test_apply_new_type_new(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """TYPE_NEW: Neuer Type + erster Suffix werden angelegt."""
    win = make_camera_window(dummy_main)
    try:
        iid = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        win.item = iid
        win.text = "DIATISCH"
        win.tag = "camera"
        win.camera = "DIATISCH"
        win.camera_new_type()
        win.new_text(win.entry_type, "VIDEO")
        win.new_text(win.entry_suffix, "MP4")
        win.apply_new()

        import dateimeister_config_xml as DX
        result = DX.get_cameras_types_suffixes(tmp_xml)
        assert "VIDEO" in result["DIATISCH"]
        assert "MP4" in result["DIATISCH"]["VIDEO"]
    finally:
        win.close_handler()


def test_apply_new_type_rename(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """TYPE_RENAME: Type wird umbenannt."""
    win = make_camera_window(dummy_main)
    try:
        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")
        win.item = iid_type
        win.text = "JPEG"
        win.tag = "type"
        win.camera, win.ctype, _ = win.get_camera_type(iid_type)
        win.type_change()
        win.new_text(win.entry_type, "RAW")
        win.apply_new()

        import dateimeister_config_xml as DX
        result = DX.get_cameras_types_suffixes(tmp_xml)
        assert "RAW" in result["DIATISCH"]
        assert "JPEG" not in result["DIATISCH"]
    finally:
        win.close_handler()


def test_apply_new_type_delete(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """TYPE_DELETE: Type wird komplett entfernt."""
    win = make_camera_window(dummy_main)
    try:
        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")
        win.item = iid_type
        win.text = "JPEG"
        win.tag = "type"
        win.camera, win.ctype, _ = win.get_camera_type(iid_type)
        win.type_delete()

        import dateimeister_config_xml as DX
        result = DX.get_cameras_types_suffixes(tmp_xml)
        assert "JPEG" not in result["DIATISCH"]
    finally:
        win.close_handler()


def test_apply_new_type_subdir(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """TYPE_SUBDIR: subdir wird geändert."""
    win = make_camera_window(dummy_main)
    try:
        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")
        win.item = iid_type
        win.text = "JPEG"
        win.tag = "type"
        win.camera, win.ctype, _ = win.get_camera_type(iid_type)
        win.type_subdir()
        win.new_text(win.entry_subdir, "NeuesSubdir")
        win.apply_new()

        import dateimeister_config_xml as DX
        result = DX.get_subdirs_per_camera(tmp_xml)
        assert result["DIATISCH"]["JPEG"] == "NeuesSubdir"
    finally:
        win.close_handler()


# ======================================================================
# 4. Suffix-Aktionen
# ======================================================================

def test_apply_new_suffix_new(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """SUFFIX_NEW: Neuer Suffix wird angelegt."""
    win = make_camera_window(dummy_main)
    try:
        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")
        win.item = iid_type
        win.text = "JPEG"
        win.tag = "type"
        win.camera, win.ctype, _ = win.get_camera_type(iid_type)
        win.type_new_suffix()
        win.new_text(win.entry_suffix, "PNG")
        win.apply_new()

        import dateimeister_config_xml as DX
        result = DX.get_cameras_types_suffixes(tmp_xml)
        assert "PNG" in result["DIATISCH"]["JPEG"]
    finally:
        win.close_handler()


def test_apply_new_suffix_rename(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """SUFFIX_RENAME: Suffix wird umbenannt."""
    win = make_camera_window(dummy_main)
    try:
        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")
        iid_suf = find_child_iid_by_text(win.tv, iid_type, "JPG", tag="suffix")
        win.item = iid_suf
        win.text = "JPG"
        win.tag = "suffix"
        win.camera, win.ctype, win.suffix, _ = win.get_camera_type_suffix(iid_suf)
        win.suffix_change()
        win.new_text(win.entry_suffix, "JP2")
        win.apply_new()

        import dateimeister_config_xml as DX
        result = DX.get_cameras_types_suffixes(tmp_xml)
        assert "JP2" in result["DIATISCH"]["JPEG"]
        assert "JPG" not in result["DIATISCH"]["JPEG"]
    finally:
        win.close_handler()


def test_apply_new_suffix_delete(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """SUFFIX_DELETE: Suffix wird entfernt."""
    win = make_camera_window(dummy_main)
    try:
        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")
        iid_suf = find_child_iid_by_text(win.tv, iid_type, "JPG", tag="suffix")
        win.item = iid_suf
        win.text = "JPG"
        win.tag = "suffix"
        win.camera, win.ctype, win.suffix, _ = win.get_camera_type_suffix(iid_suf)
        win.suffix_delete()

        import dateimeister_config_xml as DX
        result = DX.get_cameras_types_suffixes(tmp_xml)
        assert "JPG" not in result["DIATISCH"]["JPEG"]
        assert "JPEG" in result["DIATISCH"]["JPEG"]
    finally:
        win.close_handler()


def test_apply_new_process_image(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """PROCESS_IMAGE: process_image wird geändert."""
    win = make_camera_window(dummy_main)
    try:
        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")
        iid_suf = find_child_iid_by_text(win.tv, iid_type, "JPG", tag="suffix")
        win.item = iid_suf
        win.text = "JPG"
        win.tag = "suffix"
        win.camera, win.ctype, win.suffix, _ = win.get_camera_type_suffix(iid_suf)
        win.suffix_process_image()
        win.new_text(win.entry_process_image, "VIDEO")
        win.apply_new()

        import dateimeister_config_xml as DX
        result = DX.get_process_image_per_camera(tmp_xml)
        assert result["DIATISCH"]["JPEG"]["JPG"] == "VIDEO"
    finally:
        win.close_handler()


# ======================================================================
# 5. Cancel, Kontextmenü, Historisierung
# ======================================================================

def test_cancel_new_resets_dialog_state(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """cancel_new() deaktiviert alle Felder, entsperrt das Treeview."""
    win = make_camera_window(dummy_main)
    try:
        win.camera_new()
        assert str(win.entry_camera.cget("state")) == "normal"
        assert win.locked is True

        win.cancel_new()

        assert str(win.entry_camera.cget("state")) == "disabled"
        assert win.locked is False
        assert str(win.button_camera_new.cget("state")) == "normal"
    finally:
        win.close_handler()


def test_context_menu_on_camera_node(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """retrieve_item auf Kamera-Knoten befüllt das Kontextmenü."""
    win = make_camera_window(dummy_main)
    try:
        iid_dia = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        assert iid_dia is not None

        win.tv.focus(iid_dia)
        win.tv.selection_set(iid_dia)
        win.item = iid_dia
        win.text = "DIATISCH"
        win.tag = "camera"
        win.event = None
        win.context_menu_required = True
        win.retrieve_item(_make_fake_event())

        labels = []
        for i in range(win.context_menu.index("end") + 1):
            labels.append(win.context_menu.entrycget(i, "label"))
        assert any("new type" in l for l in labels), labels
        assert any("change" in l for l in labels), labels
        assert any("delete" in l for l in labels), labels
    finally:
        win.close_handler()


def test_context_menu_on_type_node(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """retrieve_item auf Type-Knoten befüllt das Kontextmenü."""
    win = make_camera_window(dummy_main)
    try:
        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")

        win.tv.focus(iid_type)
        win.tv.selection_set(iid_type)
        win.item = iid_type
        win.text = "JPEG"
        win.tag = "type"
        win.event = None
        win.context_menu_required = True
        win.retrieve_item(_make_fake_event())

        labels = []
        for i in range(win.context_menu.index("end") + 1):
            labels.append(win.context_menu.entrycget(i, "label"))
        assert any("new suffix" in l for l in labels), labels
        assert any("subdir" in l for l in labels), labels
    finally:
        win.close_handler()


def test_context_menu_on_suffix_node(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """retrieve_item auf Suffix-Knoten befüllt das Kontextmenü."""
    win = make_camera_window(dummy_main)
    try:
        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")
        iid_suf = find_child_iid_by_text(win.tv, iid_type, "JPG", tag="suffix")

        win.tv.focus(iid_suf)
        win.tv.selection_set(iid_suf)
        win.item = iid_suf
        win.text = "JPG"
        win.tag = "suffix"
        win.event = None
        win.context_menu_required = True
        win.retrieve_item(_make_fake_event())

        labels = []
        for i in range(win.context_menu.index("end") + 1):
            labels.append(win.context_menu.entrycget(i, "label"))
        assert any("process_image" in l for l in labels), labels
    finally:
        win.close_handler()


def test_apply_new_calls_historize(
        tk_root, tmp_xml, dummy_main, globals_event_manager,
        globals_screen, globals_datadir, fake_ur, silence_tooltips):
    """Nach apply_new() wächst der Undo/Redo-Stack."""
    win = make_camera_window(dummy_main)
    try:
        before = win.UR.get_processid_akt()

        iid_cam = find_iid_by_text(win.tv, "DIATISCH", tag="camera")
        iid_type = find_child_iid_by_text(win.tv, iid_cam, "JPEG", tag="type")
        win.item = iid_type
        win.text = "JPEG"
        win.tag = "type"
        win.camera, win.ctype, _ = win.get_camera_type(iid_type)
        win.type_subdir()
        win.new_text(win.entry_subdir, "HistSubdir")
        win.apply_new()

        after = win.UR.get_processid_akt()
        assert after > before, "historize_process wurde nicht aufgerufen"
    finally:
        win.close_handler()
        