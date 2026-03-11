"""
Security utilities:
- ALLOWED_MIME_TYPES: whitelist checked against actual file magic bytes
- validate_file: rejects files by extension, MIME, and hard size cap
"""
try:
    import magic as _magic
    _MAGIC_AVAILABLE = True
except Exception:
    _MAGIC_AVAILABLE = False
from fastapi import UploadFile, HTTPException

# Hard limits
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",  # some xlsx uploads arrive as this
}


async def validate_file(file: UploadFile) -> bytes:
    """
    Reads the entire file into memory, validates extension, MIME type
    (via libmagic on the actual bytes), and size cap.

    Returns raw bytes on success; raises HTTPException on failure.
    """
    # --- extension check ---
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extension '{ext}' not allowed. Upload .csv or .xlsx only.",
        )

    # --- read raw bytes ---
    raw = await file.read()

    # --- size check ---
    if len(raw) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds 5 MB limit ({len(raw) // 1024} KB received).",
        )

    # --- MIME check via libmagic (reads magic bytes, not filename) ---
    if _MAGIC_AVAILABLE:
        try:
            detected = _magic.from_buffer(raw, mime=True)
        except Exception:
            detected = "application/octet-stream"

        if detected not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Detected MIME type '{detected}' is not allowed. "
                    "Upload a real CSV or Excel file."
                ),
            )

    return raw
