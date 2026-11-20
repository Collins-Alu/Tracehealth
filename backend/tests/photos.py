"""Synthetic test photos generated in memory (no real images are used)."""

import io

from PIL import Image


def jpeg_bytes(size=(640, 480), with_gps_exif=False, orientation=None) -> bytes:
    img = Image.new("RGB", size, (90, 120, 60))
    exif = Image.Exif()
    if with_gps_exif:
        exif[0x0110] = "TestPhone Model X"  # camera model
        gps = exif.get_ifd(0x8825)
        gps[1] = "S"
        gps[2] = (1.0, 17.0, 31.0)
        gps[3] = "E"
        gps[4] = (36.0, 49.0, 18.0)
    if orientation:
        exif[0x0112] = orientation
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif.tobytes() if len(exif) else b"")
    return out.getvalue()


def png_bytes(size=(320, 240)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(out, format="PNG")
    return out.getvalue()
