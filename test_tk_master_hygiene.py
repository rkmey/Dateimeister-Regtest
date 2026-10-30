# -*- coding: utf-8 -*-
"""
Projektweite Tk-Interpreter-Hygiene: ImageTk.PhotoImage immer mit master=.

Hintergrund (Bug-Historie)
==========================

Symptom
-------
In der Regressionstestsuite (regtest/) schlugen zwei Ablauftests fehl:

    test_journey_safety.py::test_journey_does_not_touch_real_datadir
    test_journey_safety.py::test_journey_does_not_touch_vorrat

mit:

    _tkinter.TclError: image "pyimageNNN" doesn't exist

Der Fehler trat in display_images() auf, an der Stelle

    self.canvas_gallery.create_image(..., image=pimg, ...)

Ursache
-------
PIL.ImageTk.PhotoImage(...) wurde an mehreren Stellen ohne master=
aufgerufen. Ohne master= bindet ImageTk das Bild an tkinter._default_root.
Die Test-Fixur journey_app erzeugt pro Test eine eigene tk.Tk()-Instanz
und zerstoert sie im Teardown wieder. Nach dem ersten Test zeigte
_default_root also auf eine bereits zerstoerte Tk-Instanz, waehrend die
Bilder des naechsten Tests im (neuen) Canvas-Interpreter registriert
werden mussten. Ergebnis: create_image() im richtigen Canvas fand das
Bild nicht -> TclError.

Der eigentliche Ausloeser war der Video-Zweig: VideoPlayer.
_render_frame_to_photo() erzeugte das PhotoImage ohne master=. Die
STILL- und RAW-Zweige (tools.new_image, display_images) hatten dasselbe
Problem, waren aber im Test nicht der ausloesende Pfad.

Fix
---
1. VideoPlayer._render_frame_to_photo():
       ImageTk.PhotoImage(image=..., master=self.canvas)
2. tools.new_image(): neuer Parameter master=None, an ImageTk.
   PhotoImage durchgereicht.
3. display_images(): alle Aufrufe von tools.new_image / ImageTk.
   PhotoImage mit master=self.canvas_gallery.
4. Zusaetzlich: analoge Stellen in Dateimeister_FSimage.py,
   Dateimeister_FSVideo.py, Dateimeister_Duplicates.py, print_preview.py
   pruefen und ergaenzen.

Die Invariante ist: ein PhotoImage, das auf einem Widget W angezeigt
wird, muss im selben Tk-Interpreter registriert sein wie W. In Python
ausgedrueckt: photo.tk is widget.tk.

Die Tests unten nageln genau diese Invariante fest. Sie wuerden
fehlschlagen, sobald jemand irgendwo wieder master= vergisst.
"""

import tkinter as tk

import pytest


# ----------------------------------------------------------------------
# tools.new_image
# ----------------------------------------------------------------------
def test_new_image_uses_given_master(tk_root, test_image):
    """tools.new_image muss das PhotoImage im Interpreter des uebergebenen
    Master registrieren, nicht im Default-Root.

    Ohne master= landet das Bild in tkinter._default_root. In einem
    Prozess mit mehreren tk.Tk()-Instanzen (Tests, Plugins, eingebettete
    Nutzung) ist das die falsche - und ggf. schon zerstoerte - Instanz.
    """
    import tools

    frame = tk.Frame(tk_root)
    try:
        pimg, w, h = tools.new_image(
            file=test_image, height=100, master=frame
        )
        assert pimg is not None
        assert w > 0 and h > 0
        # Entscheidend: das PhotoImage haengt am selben Tk-Interpreter
        # wie der uebergebene Master.
        assert pimg.tk is frame.tk, (
            "PhotoImage wurde nicht im Interpreter des Masters erzeugt. "
            "master= in tools.new_image() vergessen?"
        )
    finally:
        frame.destroy()


# ----------------------------------------------------------------------
# VideoPlayer
# ----------------------------------------------------------------------
def test_video_player_photo_uses_canvas_as_master(tk_root):
    """VideoPlayer._render_frame_to_photo muss das PhotoImage am
    Canvas-Interpreter registrieren. Ohne master= landet es am Default-
    Root und ist fuer den Canvas nicht sichtbar (TclError pyimageNNN).

    Wir bauen den Player ohne __init__, damit kein echter MediaPlayer
    gestartet wird. _render_frame_to_photo() wird mit einem synthetischen
    ffpyplayer-Image-Objekt aufgerufen.
    """
    import dateimeister_video as DV

    canvas = tk.Canvas(tk_root, width=200, height=100)
    canvas.pack()
    try:
        player = DV.VideoPlayer.__new__(DV.VideoPlayer)
        player.window = tk_root
        player.video_source = "dummy"
        player.canvas = canvas
        player.debug = False
        player.my_tag = "test"

        class _FakeImageObj:
            """Minimales Double fuer ein ffpyplayer-Image."""
            def get_size(self):
                return (4, 3)

            def to_bytearray(self):
                return bytes(4 * 3 * 3)  # 4x3 RGB, alles 0

        photo = player._render_frame_to_photo(_FakeImageObj())
        assert photo is not None
        assert photo.tk is canvas.tk, (
            "VideoPlayer._render_frame_to_photo() hat das PhotoImage nicht "
            "im Canvas-Interpreter erzeugt. master=self.canvas vergessen?"
        )
    finally:
        canvas.destroy()


# ----------------------------------------------------------------------
# Optional: project-wide guard
# ----------------------------------------------------------------------
def test_no_imagetk_photoimage_without_master_in_program_dir(program_dir):
    """Statischer Check: kein ImageTk.PhotoImage(...) ohne master= im
    Programmcode. ..."""
    import os
    import re

    if not os.path.isdir(program_dir):
        pytest.skip("Programmverzeichnis nicht gefunden: %s" % program_dir)

    pattern = re.compile(r"ImageTk\.PhotoImage\s*\(")
    problems = []

    for fname in sorted(os.listdir(program_dir)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(program_dir, fname)
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
        except (OSError, UnicodeDecodeError):
            continue

        for i, line in enumerate(lines):
            if line.lstrip().startswith("#"):
                continue
            if not pattern.search(line):
                continue
            # Klammer-Zaehlung bis zum Ende des Aufrufs
            depth = 0
            buf = []
            j = i
            while j < len(lines):
                depth += lines[j].count("(") - lines[j].count(")")
                buf.append(lines[j].rstrip())
                j += 1
                if depth <= 0:
                    break
            call_text = "\n".join(buf)
            if "master" not in call_text:
                problems.append(f"{fname}:{i + 1}:\n    {call_text}")

    assert not problems, (
        "ImageTk.PhotoImage(...) ohne master= gefunden. Bitte master= "
        "mit dem Widget ergaenzen, auf dem das Bild angezeigt wird:\n\n  "
        + "\n\n  ".join(problems)
    )