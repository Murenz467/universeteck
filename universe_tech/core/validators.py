"""Upload safety: allow-list of file types, size limit and a real content check for common formats."""
import os
from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED = {
    "pdf", "png", "jpg", "jpeg", "gif", "webp", "txt", "csv", "md", "zip",
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "mp4", "mov", "mp3", "wav",
}
# first bytes that prove the content matches the extension (types not listed are checked by extension only)
MAGIC = {
    "pdf": [b"%PDF"], "png": [b"\x89PNG"], "jpg": [b"\xff\xd8\xff"], "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF87a", b"GIF89a"], "webp": [b"RIFF"], "zip": [b"PK\x03\x04", b"PK\x05\x06"],
    "docx": [b"PK\x03\x04"], "xlsx": [b"PK\x03\x04"], "pptx": [b"PK\x03\x04"],
    "doc": [b"\xd0\xcf\x11\xe0"], "xls": [b"\xd0\xcf\x11\xe0"], "ppt": [b"\xd0\xcf\x11\xe0"],
}


def validate_upload(f):
    ext = os.path.splitext(f.name)[1].lower().lstrip(".")
    if ext not in ALLOWED:
        raise ValidationError(f"Files of type .{ext or '?'} are not allowed. Allowed: {', '.join(sorted(ALLOWED))}.")
    if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValidationError(f"File is larger than {settings.MAX_UPLOAD_MB} MB.")
    if ext in MAGIC:
        pos = f.tell() if hasattr(f, "tell") else 0
        head = f.read(8)
        f.seek(pos)
        if not any(head.startswith(m) for m in MAGIC[ext]):
            raise ValidationError("The file content does not match its extension.")
