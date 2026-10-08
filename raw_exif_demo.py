# raw_exif_test.py
import io, sys
import rawpy
from PIL import Image, ExifTags

file = sys.argv[1]
with rawpy.imread(file) as raw:
    thumb = raw.extract_thumb()
    if thumb.format == rawpy.ThumbFormat.JPEG:
        img = Image.open(io.BytesIO(thumb.data))
        exif = img.getexif()
        for tag_id, value in exif.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            print(f"{tag:30s} = {value!r}")
    else:
        print("Kein JPEG-Thumbnail vorhanden")