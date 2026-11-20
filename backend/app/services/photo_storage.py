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

Files are stored under UPLOAD_DIR with a random name. They are never served
directly from a public folder; the API checks permissions on every download.
A cloud (S3-compatible) backend will implement the same functions for
deployment.
"""

import io
import uuid
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings

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
    """Store the processed photo and return its storage key (a relative path)."""
    now = datetime.now(UTC)
    key = f"reports/{now:%Y}/{now:%m}/{uuid.uuid4().hex}.jpg"
    path = _path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(jpeg_bytes)
    return key


def delete_photo(key: str) -> None:
    try:
        _path_for(key).unlink(missing_ok=True)
    except ValueError:
        pass


def open_photo_path(key: str) -> Path | None:
    path = _path_for(key)
    return path if path.is_file() else None


def _path_for(key: str) -> Path:
    root = get_settings().UPLOAD_DIR.resolve()
    path = (root / key).resolve()
    if root not in path.parents:  # blocks "../../etc/passwd" style keys
        raise ValueError("invalid storage key")
    return path
