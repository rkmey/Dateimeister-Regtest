# -*- coding: utf-8 -*-
"""
Safety-Tests: Die Ablauftests duerfen weder das echte Datenverzeichnis
noch den Vorrat anfassen.
"""

import hashlib
import os
from pathlib import Path

import pytest

REGTest_DIR   = os.path.dirname(os.path.abspath(__file__))
TESTDATEN_DIR = os.path.dirname(REGTest_DIR)
VORRAT_INDIR  = os.path.join(TESTDATEN_DIR, "regtest", "regtest-images")


def _dir_fingerprint(path):
    """Hash ueber alle Dateien unter path (rekursiv, mit mtime und Groesse)."""
    h = hashlib.sha256()
    for f in sorted(Path(path).rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(path)).encode())
            h.update(str(f.stat().st_mtime_ns).encode())
            h.update(str(f.stat().st_size).encode())
    return h.hexdigest()


def test_journey_does_not_touch_real_datadir(journey_app, journey_dirs):
    """Das echte Datenverzeichnis bleibt unveraendert."""
    real_datadir = os.path.join(TESTDATEN_DIR, "daten")
    if not os.path.isdir(real_datadir):
        pytest.skip("Echtes datadir fehlt: %s" % real_datadir)

    before = _dir_fingerprint(real_datadir)

    app = journey_app
    app.o_camera.delete(0, "end")
    app.o_camera.insert(0, "OTHER")
    app.dict_cameras, app.dict_subdirs, app.dict_process_image = \
        app.get_camera_xml(camera="OTHER")
    app.lb_gen.delete(0, "end")
    for t in app.dict_cameras.get("OTHER", {}):
        app.lb_gen.insert("end", t)
    app.dict_gen_files_keys = list(app.dict_cameras.get("OTHER", {}))
    for i, t in enumerate(app.dict_gen_files_keys):
        if t in ("JPEG", "RAW", "VIDEO"):
            app.lb_gen.selection_set(i)
    app.imagetypes_click_order = [
        i for i, t in enumerate(app.dict_gen_files_keys)
        if t in ("JPEG", "RAW", "VIDEO")]

    app.Button_generate_pressed()
    app.root.update_idletasks()

    after = _dir_fingerprint(real_datadir)
    assert before == after, (
        "Der Test hat in %s geschrieben. Die Test-Ini ist "
        "fehlerhaft umgebogen." % real_datadir)


def test_journey_does_not_touch_vorrat(journey_app, journey_dirs):
    """Der Vorrat bleibt unveraendert (indir wird vom Generator nur gelesen)."""
    if not os.path.isdir(VORRAT_INDIR):
        pytest.skip("Vorrat fehlt: %s" % VORRAT_INDIR)

    before = _dir_fingerprint(VORRAT_INDIR)

    app = journey_app
    app.o_camera.delete(0, "end")
    app.o_camera.insert(0, "OTHER")
    app.dict_cameras, app.dict_subdirs, app.dict_process_image = \
        app.get_camera_xml(camera="OTHER")
    app.lb_gen.delete(0, "end")
    for t in app.dict_cameras.get("OTHER", {}):
        app.lb_gen.insert("end", t)
    app.dict_gen_files_keys = list(app.dict_cameras.get("OTHER", {}))
    for i, t in enumerate(app.dict_gen_files_keys):
        if t in ("JPEG", "RAW", "VIDEO"):
            app.lb_gen.selection_set(i)
    app.imagetypes_click_order = [
        i for i, t in enumerate(app.dict_gen_files_keys)
        if t in ("JPEG", "RAW", "VIDEO")]

    app.Button_generate_pressed()
    app.root.update_idletasks()

    after = _dir_fingerprint(VORRAT_INDIR)
    assert before == after, (
        "Der Test hat in den Vorrat geschrieben: %s. Das sollte nicht "
        "passieren - der Generator liest nur." % VORRAT_INDIR)