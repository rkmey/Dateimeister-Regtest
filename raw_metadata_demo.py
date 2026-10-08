# -*- coding: utf-8 -*-
"""
raw_metadata_test.py - Diagnose-Skript fuer rawpy-Metadaten.

Aufruf:
    python raw_metadata_test.py "C:\\Pfad\\zu\\datei.NEF"

Zeigt alles, was rawpy fuer eine RAW-Datei an Metadaten liefert.
Damit sehen wir, welche Felder pro Kamera/Format tatsaechlich gefuellt sind.
"""

import sys
import os

import rawpy


def dump(obj, name):
    """Gibt alle Attribute eines Objekts aus, die nicht mit _ beginnen."""
    print(f"\n=== {name} ===")
    if obj is None:
        print("  (None)")
        return
    for attr in sorted(dir(obj)):
        if attr.startswith("_"):
            continue
        try:
            value = getattr(obj, attr)
            if callable(value):
                continue
            print(f"  {attr:30s} = {value!r}")
        except Exception as e:
            print(f"  {attr:30s} = <Fehler: {e}>")


def analyze(file):
    if not os.path.isfile(file):
        print(f"Datei nicht gefunden: {file}")
        return 1

    print(f"Datei: {file}")
    print(f"Groesse: {os.path.getsize(file) / (1024*1024):.1f} MB")

    with rawpy.imread(file) as raw:
        # ---- Sensorgroesse ----
        print(f"\n=== Sensorgroesse ===")
        print(f"  width  = {raw.sizes.width}")
        print(f"  height = {raw.sizes.height}")
        print(f"  raw_type = {raw.raw_type}")
        print(f"  num_colors = {raw.num_colors}")

        # ---- Kameradaten (Attribute direkt am raw-Objekt) ----
        print(f"\n=== Kameradaten (direkte Attribute) ===")
        for attr in ("camera_manufacturer", "camera_model", "color_desc",
                     "raw_pattern", "camera_whitebalance", "daylight_whitebalance",
                     "black_level_per_channel", "white_level"):
            try:
                value = getattr(raw, attr, "<nicht vorhanden>")
                print(f"  {attr:30s} = {value!r}")
            except Exception as e:
                print(f"  {attr:30s} = <Fehler: {e}>")

        # ---- metadata ----
        try:
            meta = raw.metadata
            dump(meta, "raw.metadata")
        except Exception as e:
            print(f"\nraw.metadata nicht verfuegbar: {e}")

        # ---- other ----
        try:
            other = raw.other
            dump(other, "raw.other")
        except Exception as e:
            print(f"\nraw.other nicht verfuegbar: {e}")

    print("\nFertig.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Aufruf: python raw_metadata_test.py <pfad-zur-raw-datei>")
        sys.exit(1)
    sys.exit(analyze(sys.argv[1]))