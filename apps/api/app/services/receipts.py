"""Receipt upload validation and storage.

- size limit enforced while reading (never trust Content-Length)
- type detected from the bytes by Pillow, not from the file name or Content-Type
- image is re-encoded: strips EXIF/GPS metadata and any appended payload
- random file name, 0600 permissions, stored outside any public directory
"""

import asyncio
import contextlib
import io
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import get_settings

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PIXELS = 40_000_000  # decompression-bomb guard (~ 8000 x 5000)
_CHUNK = 64 * 1024


def _upload_dir() -> Path:
    path = Path(get_settings().upload_dir).resolve()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    buf = bytearray()
    while chunk := await file.read(_CHUNK):
        buf.extend(chunk)
        if len(buf) > limit:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail="file_too_large")
    return bytes(buf)


def _reencode(data: bytes) -> tuple[bytes, str]:
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format or ""
            if fmt not in ALLOWED_FORMATS:
                raise ValueError("format")
            if probe.width * probe.height > MAX_PIXELS:
                raise ValueError("too many pixels")
            probe.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            out = io.BytesIO()
            if fmt == "JPEG":
                img.convert("RGB").save(out, format="JPEG", quality=90)
            elif fmt == "PNG":
                img.save(out, format="PNG", optimize=True)
            else:
                img.save(out, format="WEBP", quality=90)
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="invalid_image") from exc
    return out.getvalue(), ALLOWED_FORMATS[fmt]


def _write(data: bytes, ext: str) -> str:
    name = f"{uuid.uuid4().hex}.{ext}"
    path = _upload_dir() / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return name


async def save_receipt(file: UploadFile) -> str:
    """Validate and store an uploaded receipt. Returns the stored random file name."""
    if (file.content_type or "").lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="invalid_image")
    data = await _read_limited(file, get_settings().receipt_max_bytes)
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="empty_file")
    clean, ext = await asyncio.to_thread(_reencode, data)
    return await asyncio.to_thread(_write, clean, ext)


def receipt_path(name: str) -> Path:
    """Resolve a stored name to a path, refusing anything that escapes UPLOAD_DIR."""
    base = _upload_dir()
    path = (base / name).resolve()
    if path.parent != base:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return path


def delete_receipt(name: str) -> None:
    with contextlib.suppress(HTTPException):
        receipt_path(name).unlink(missing_ok=True)
