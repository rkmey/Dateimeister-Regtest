# -*- coding: utf-8 -*-
"""
raw_test.py - kleines Diagnose-Skript fuer rawpy mit einer echten NEF.

Aufruf:
    python raw_test.py "C:\\Pfad\\zu\\deiner\\datei.NEF"

Zeigt:
    * Grunddaten der Datei (Kamera, Sensor-Groesse)
    * ob ein eingebettetes Thumbnail existiert (schneller Weg)
    * wie lange postprocess() dauert (langsamer Weg)
    * was fuer ein Bild dabei herauskommt
"""

import sys
import os
import time
import io

import rawpy
from PIL import Image


def analyze(nef_path):
    if not os.path.isfile(nef_path):
        print(f"Datei nicht gefunden: {nef_path}")
        return 1

    size_mb = os.path.getsize(nef_path) / (1024 * 1024)
    print(f"Datei:        {nef_path}")
    print(f"Groesse:      {size_mb:.1f} MB")
    print()

    # ---------- 1. Grunddaten ----------
    print("=== Grunddaten ===")
    t0 = time.perf_counter()
    with rawpy.imread(nef_path) as raw:
        t_open = time.perf_counter() - t0
        print(f"Open-Zeit:    {t_open*1000:.1f} ms")
        print(f"Sensor:       {raw.sizes.width} x {raw.sizes.height}")
        print(f"Raw-Format:   {raw.raw_type}")
        # Kamera-Modell steht in den Metadaten, nicht immer verfuegbar:
        try:
            print(f"Kamera:       {raw.camera_manufacturer} {raw.camera_model}")
        except AttributeError:
            print("Kamera:       (nicht verfuegbar)")

        # ---------- 2. Eingebettetes Thumbnail ----------
        print()
        print("=== Eingebettetes Thumbnail (schneller Weg) ===")
        try:
            t0 = time.perf_counter()
            thumb = raw.extract_thumb()
            t_thumb = time.perf_counter() - t0
            print(f"Extrakt-Zeit: {t_thumb*1000:.1f} ms")
            print(f"Format:       {thumb.format}")
            if thumb.format == rawpy.ThumbFormat.JPEG:
                img = Image.open(io.BytesIO(thumb.data))
                print(f"JPEG-Groesse: {img.size[0]} x {img.size[1]}")
                print(f"JPEG-Bytes:   {len(thumb.data)}")
            else:
                print(f"Bitmap-Form:  {thumb.data.shape}")
        except rawpy.LibRawNoThumbnailError:
            print("KEIN eingebettetes Thumbnail vorhanden.")
        except Exception as e:
            print(f"Fehler beim Thumbnail-Extrakt: {type(e).__name__}: {e}")

        # ---------- 3. postprocess() ----------
        print()
        print("=== postprocess() (langsamer Weg) ===")
        t0 = time.perf_counter()
        rgb = raw.postprocess(use_camera_wb=True)
        t_pp = time.perf_counter() - t0
        print(f"postprocess:  {t_pp*1000:.1f} ms")
        print(f"RGB-Form:     {rgb.shape}")

    # ---------- 4. Speichern zum Anschauen ----------
    print()
    print("=== Speichern zum Anschauen ===")
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "artifacts", "rawtest")
    os.makedirs(out_dir, exist_ok=True)

    # Vorschau (Thumbnail)
    try:
        with rawpy.imread(nef_path) as raw:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                img = Image.open(io.BytesIO(thumb.data))
                out_thumb = os.path.join(out_dir, "preview_thumb.jpg")
                img.save(out_thumb)
                print(f"Thumbnail gespeichert: {out_thumb}")
    except Exception as e:
        print(f"Thumbnail konnte nicht gespeichert werden: {e}")

    # Vorschau (postprocess)
    img_full = Image.fromarray(rgb)
    out_full = os.path.join(out_dir, "preview_full.jpg")
    # Auf maximal 2000 Pixel Breite reduzieren, damit die Datei handlich bleibt
    img_full.thumbnail((2000, 2000))
    img_full.save(out_full, quality=90)
    print(f"Volle Vorschau gespeichert: {out_full}")

    print()
    print("Fertig.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Aufruf: python raw_test.py <pfad-zur-nef>")
        sys.exit(1)
    sys.exit(analyze(sys.argv[1]))