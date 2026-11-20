"""
Report photo storage (decision D6, privacy decision D12).

Every uploaded photo is:
  1. checked to really be an image (not just named .jpg) and not too large,
  2. rotated upright using its EXIF orientation,
  3. shrunk to at most PHOTO_MAX_DIMENSION pixels on the longest side
     (smaller files for verifiers on slow connections),
  4. re-encoded as a fresh JPEG. Re-encoding drops ALL metadata: the phone's
     GPS position, model, owner name and timestamps. The report's location is
     stored separately on purpose, and only after the reporter confirmed it.

Files are stored with a random name by the configured backend (app/storage:
local disk or S3-compatible object storage). They are never served from a
public folder; the API checks permissions on every download.
"""

import io
import uuid
from datetime import UTC, datetime

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.storage import get_storage

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
# Refuse "decompression bombs": tiny files that expand to gigantic images
Image.MAX_IMAGE_PIXELS = 50_000_000


class PhotoError(ValueError):
    """A plain-language reason the photo was refused."""


def process_photo(raw: bytes) -> bytes:
    settings = get_settings()
    if not raw:
        raise PhotoError("The photo is empty. Please take the photo again.")
    if len(raw) > settings.MAX_PHOTO_MB * 1024 * 1024:
        raise PhotoError(f"The photo is too large. The limit is {settings.MAX_PHOTO_MB} MB.")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format
            probe.verify()  # detects truncated/corrupt files
        if fmt not in ALLOWED_FORMATS:
            raise PhotoError("Please upload a JPEG, PNG or WebP photo.")
        with Image.open(io.BytesIO(raw)) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((settings.PHOTO_MAX_DIMENSION, settings.PHOTO_MAX_DIMENSION))
            out = io.BytesIO()
            # No exif= argument, so the new file carries no metadata
            img.save(out, format="JPEG", quality=82, optimize=True)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise PhotoError("This file is not a readable photo. Please try again.") from None


def save_photo(jpeg_bytes: bytes) -> str:
    """Store the processed photo and return its storage key."""
    now = datetime.now(UTC)
    key = f"reports/{now:%Y}/{now:%m}/{uuid.uuid4().hex}.jpg"
    get_storage().save(key, jpeg_bytes)
    return key


def read_photo(key: str) -> bytes | None:
    return get_storage().read(key)


def delete_photo(key: str) -> None:
    try:
        get_storage().delete(key)
    except Exception:
        pass  # a leftover file is harmless; never fail a request because of it
