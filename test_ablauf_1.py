# -*- coding: utf-8 -*-
"""
Ablauftests fuer das Main Window.

Laufen ueber den echten init()-Weg mit eigener Test-Ini und eigener
Test-Config-XML in der Sandbox. indir ist der Vorrat direkt.

Kamera im Test: OTHER mit allen drei Typen (JPEG, RAW, VIDEO).
"""

import os

import pytest

import tools


def _setup_camera_and_types(app, camera="OTHER", types=("JPEG",)):
    """Setzt Kamera und Typ-Auswahl im Main Window, wie es der User
    ueber den Kamera-Dialog tun wuerde."""
    app.o_camera.delete(0, "end")
    app.o_camera.insert(0, camera)

    app.dict_cameras, app.dict_subdirs, app.dict_process_image = \
        app.get_camera_xml(camera=camera)

    app.lb_gen.delete(0, "end")
    for t in app.dict_cameras.get(camera, {}):
        app.lb_gen.insert("end", t)
    app.dict_gen_files_keys = list(app.dict_cameras.get(camera, {}))
    for i, t in enumerate(app.dict_gen_files_keys):
        if t in types:
            app.lb_gen.selection_set(i)
    app.imagetypes_click_order = [
        i for i, t in enumerate(app.dict_gen_files_keys) if t in types]


# ======================================================================
# Der Ablauftest
# ======================================================================

def test_journey_generate_duplicates_then_addrelpath(journey_app):
    """Ablauf wie vom User:

    1. Kamera OTHER, Typen JPEG, RAW, VIDEO.
    2. Generate (Dateien aus dem Vorrat).
    3. Duplikate vorhanden: Button 'Show duplicates' enabled.
    4. addrelpath an, neu generieren.
    5. Duplikate weg: Button 'Show duplicates' disabled.
    """
    app = journey_app

    _setup_camera_and_types(app, camera="OTHER",
                            types=("JPEG", "RAW", "VIDEO"))

    # 1. Generate
    app.Button_generate_pressed()
    app.root.update_idletasks()

    imagetype = tools.Globals.imagetype
    print("[journey] imagetype=%s" % imagetype)
    assert imagetype == "JPEG-RAW-VIDEO", (
        "Erwartete imagetype='JPEG-RAW-VIDEO', bekommen: %r" % imagetype)

    dupl_dict = tools.Globals.dict_duplicates.get(imagetype, {})
    anzahl_duplikate = sum(
        1 for sources in dupl_dict.values() if len(sources) > 1)
    print("[journey] Duplikate gefunden: %d" % anzahl_duplikate)

    if anzahl_duplikate == 0:
        pytest.skip(
            "Vorrat enthaelt keine Duplikate; Ablauf nicht testbar.")

    assert str(app.button_duplicates.cget("state")) == "normal", (
        "Button 'Show duplicates' sollte bei Duplikaten enabled sein")

    # 2. addrelpath einschalten und neu generieren
    app.cb_addrelpath_var.set(1)
    app.state_gen_required()

    app.Button_generate_pressed()
    app.root.update_idletasks()

    dupl_dict_nach = tools.Globals.dict_duplicates.get(imagetype, {})
    anzahl_duplikate_nach = sum(
        1 for sources in dupl_dict_nach.values() if len(sources) > 1)
    print("[journey] Duplikate nach addrelpath: %d"
          % anzahl_duplikate_nach)

    assert anzahl_duplikate_nach == 0, (
        "Nach addrelpath sollten keine Duplikate mehr existieren, "
        "gefunden: %d" % anzahl_duplikate_nach)
    assert str(app.button_duplicates.cget("state")) == "disabled", (
        "Button 'Show duplicates' sollte ohne Duplikate disabled sein")