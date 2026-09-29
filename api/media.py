"""Where an uploaded photo or recording goes, and what is allowed to be one.

Every line here is a trust boundary. The file comes from a phone we do not
control and is served back from our own origin, so three things never come from
the client: the filename (generated), the extension (from ALLOWED, keyed on the
declared type), and the claim about what the bytes are (checked against the
first few). The extension decides the Content-Type on the way out, so "HTML that
says it is a PNG" is the whole attack. NoSniff closes the rest.
"""

import mimetypes
import os
import pathlib
import uuid

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps
from starlette.staticfiles import StaticFiles

MEDIA_DIR = pathlib.Path(os.getenv("MEDIA_DIR", "media")).resolve()
MEDIA_URL_PREFIX = "/media"

# A phone photo off a recent iPhone is 3-5 MB; a minute of AAC is under 1 MB.
# Generous enough not to reject a real submission, small enough that a loop
# cannot fill the disk before anybody notices.
MAX_PHOTO_BYTES = 12 * 1024 * 1024
MAX_AUDIO_BYTES = 25 * 1024 * 1024

# The only types that exist, the extension each one gets, and the byte prefix it
# has to actually start with. (offset, magic) - ISO base media files (m4a, mp4)
# carry theirs at offset 4, after the box length. No HEIC: every photo is
# re-encoded, Pillow cannot read HEIC, and the app asks the picker for JPEG.
ALLOWED = {
    "image/jpeg": ("photo", ".jpg", [(0, b"\xff\xd8\xff")]),
    "image/png": ("photo", ".png", [(0, b"\x89PNG\r\n\x1a\n")]),
    "image/webp": ("photo", ".webp", [(0, b"RIFF"), (8, b"WEBP")]),
    "audio/m4a": ("audio", ".m4a", [(4, b"ftyp")]),
    "audio/x-m4a": ("audio", ".m4a", [(4, b"ftyp")]),
    "audio/mp4": ("audio", ".m4a", [(4, b"ftyp")]),
    "audio/aac": ("audio", ".m4a", [(4, b"ftyp")]),
    "audio/mpeg": ("audio", ".mp3", [(0, b"ID3"), (0, b"\xff")]),
    "audio/wav": ("audio", ".wav", [(0, b"RIFF"), (8, b"WAVE")]),
    "audio/x-wav": ("audio", ".wav", [(0, b"RIFF"), (8, b"WAVE")]),
}

CHUNK = 64 * 1024

# StaticFiles types a response from the extension, using the OS mime table - so
# what we serve depended on the machine. macOS calls .m4a `audio/mp4a-latm`
# (wrong: that is LATM-framed AAC) and the Linux container had no entry at all,
# sending every recording as application/octet-stream. Pinned here so the
# Content-Type is a property of this code and not of /etc/mime.types.
SERVED_TYPES = {
    ".m4a": "audio/mp4",
    ".webp": "image/webp",
    ".wav": "audio/wav",
}
for _extension, _type in SERVED_TYPES.items():
    mimetypes.add_type(_type, _extension)


class NoSniff(StaticFiles):
    """Uploaded bytes served from our own origin, with sniffing switched off.

    The extension whitelist decides the Content-Type; this stops a browser
    overruling it on the strength of the content.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Uploads are immutable - the name is a fresh uuid every time.
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def _magic_matches(head: bytes, signatures) -> bool:
    return any(head[offset : offset + len(magic)] == magic for offset, magic in signatures)


async def save_upload(upload: UploadFile) -> tuple[str, str, str, int]:
    """Write one upload under MEDIA_DIR. Returns (path, kind, mime, bytes).

    `path` is relative and generated here; nothing derived from the client's
    filename ever reaches the filesystem.
    """
    mime = (upload.content_type or "").split(";")[0].strip().lower()
    if mime not in ALLOWED:
        raise HTTPException(status_code=415, detail=f"Unsupported media type: {mime or 'unknown'}")

    kind, extension, signatures = ALLOWED[mime]
    limit = MAX_PHOTO_BYTES if kind == "photo" else MAX_AUDIO_BYTES

    head = await upload.read(16)
    if not _magic_matches(head, signatures):
        raise HTTPException(status_code=415, detail=f"File contents are not {mime}")

    relative = f"{uuid.uuid4().hex}{extension}"
    destination = MEDIA_DIR / relative
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    try:
        with destination.open("wb") as out:
            buffer = head
            while buffer:
                written += len(buffer)
                if written > limit:
                    # Stop at the limit rather than after it: a client that
                    # ignores the documented maximum should not get to spend
                    # the whole disk proving it.
                    raise HTTPException(
                        status_code=413, detail=f"{kind} must be under {limit // (1024 * 1024)} MB"
                    )
                out.write(buffer)
                buffer = await upload.read(CHUNK)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    if written == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty file")

    if kind == "photo":
        written = _strip_metadata(destination)

    return relative, kind, mime, written


def _strip_metadata(path: pathlib.Path) -> int:
    """Re-encode a photo in place, so what we serve carries no EXIF: a phone
    photo's GPS, camera and capture time. The orientation tag goes with it, so
    it is applied to the pixels first. Returns the new size."""
    try:
        with Image.open(path) as image:
            upright = ImageOps.exif_transpose(image)
            icc = image.info.get("icc_profile")
            upright.save(path, format=image.format, icc_profile=icc)
    except Exception:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=415, detail="File is not a readable image") from None
    return path.stat().st_size


def media_url(path: str) -> str:
    return f"{MEDIA_URL_PREFIX}/{path}"
