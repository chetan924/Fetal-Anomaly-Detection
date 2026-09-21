from pathlib import Path
from typing import Set, Tuple
from fastapi import UploadFile

from app.core.config import MAX_UPLOAD_SIZE_BYTES
from app.inference.response_models import ErrorCode, InferenceException


# ============================================================
# ALLOWED IMAGE FORMATS
# ============================================================

ALLOWED_IMAGE_EXTENSIONS: Set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}

ALLOWED_IMAGE_MIME_TYPES: Set[str] = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "application/octet-stream",  # Accepted if extension matches
}

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
RIFF_MAGIC = b"RIFF"
WEBP_MAGIC = b"WEBP"


# ============================================================
# IMAGE UPLOAD VALIDATION
# ============================================================

async def validate_image_upload(
    file: UploadFile,
    model_name: str = "inference",
    max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES,
) -> Tuple[str, bytes, str]:
    """
    Validates uploaded image files without loading heavy ML libraries.
    Checks file presence, extension, content-type, size limits,
    sanitizes filename to prevent directory traversal, and verifies magic headers.
    """
    if file is None:
        raise InferenceException(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message="Image file is required.",
            model=model_name,
        )

    raw_filename = (file.filename or "").strip()
    if not raw_filename:
        raise InferenceException(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message="Filename is missing.",
            model=model_name,
        )

    # Sanitize basename to prevent path traversal (e.g., ../../evil.png)
    filename = Path(raw_filename).name
    if not filename:
        raise InferenceException(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid filename.",
            model=model_name,
        )

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise InferenceException(
            status_code=415,
            code=ErrorCode.UNSUPPORTED_FILE_TYPE,
            message=(
                f"Unsupported file extension '{ext}'. "
                f"Allowed image formats: {sorted(ALLOWED_IMAGE_EXTENSIONS)}"
            ),
            model=model_name,
        )

    content_type = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise InferenceException(
            status_code=415,
            code=ErrorCode.UNSUPPORTED_FILE_TYPE,
            message=(
                f"Unsupported content-type '{content_type}'. "
                f"Allowed image types: {sorted(ALLOWED_IMAGE_MIME_TYPES)}"
            ),
            model=model_name,
        )

    # Read content with size check
    content = await file.read()

    if not content or len(content) == 0:
        raise InferenceException(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message="Uploaded image file is empty.",
            model=model_name,
        )

    if len(content) > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise InferenceException(
            status_code=413,
            code=ErrorCode.FILE_TOO_LARGE,
            message=f"Uploaded image exceeds the maximum size limit of {max_mb} MB.",
            model=model_name,
        )

    # Magic byte signature check
    if ext == ".png" and not content.startswith(PNG_MAGIC):
        raise InferenceException(
            status_code=422,
            code=ErrorCode.VALIDATION_ERROR,
            message="Corrupted or invalid PNG image file header.",
            model=model_name,
        )
    elif ext in (".jpg", ".jpeg") and not content.startswith(JPEG_MAGIC[:2]):
        raise InferenceException(
            status_code=422,
            code=ErrorCode.VALIDATION_ERROR,
            message="Corrupted or invalid JPEG image file header.",
            model=model_name,
        )
    elif ext == ".webp":
        if not (content.startswith(RIFF_MAGIC) and len(content) > 12 and content[8:12] == WEBP_MAGIC):
            raise InferenceException(
                status_code=422,
                code=ErrorCode.VALIDATION_ERROR,
                message="Corrupted or invalid WEBP image file header.",
                model=model_name,
            )

    return filename, content, content_type


# ============================================================
# VTK 3D MESH UPLOAD VALIDATION
# ============================================================

async def validate_vtk_upload(
    file: UploadFile,
    model_name: str = "face",
    max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES,
) -> Tuple[str, bytes, str]:
    """
    Validates uploaded 3D VTK mesh files without importing VTK in Main API.
    Sanitizes filename, verifies extension, size, and header signature.
    """
    if file is None:
        raise InferenceException(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message="VTK mesh file is required.",
            model=model_name,
        )

    raw_filename = (file.filename or "").strip()
    if not raw_filename:
        raise InferenceException(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message="Filename is missing.",
            model=model_name,
        )

    filename = Path(raw_filename).name
    if not filename:
        raise InferenceException(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid filename.",
            model=model_name,
        )

    ext = Path(filename).suffix.lower()
    if ext != ".vtk":
        raise InferenceException(
            status_code=415,
            code=ErrorCode.UNSUPPORTED_FILE_TYPE,
            message="Face 3D analysis requires a .vtk mesh file.",
            model=model_name,
        )

    content_type = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()

    content = await file.read()

    if not content or len(content) == 0:
        raise InferenceException(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message="Uploaded VTK file is empty.",
            model=model_name,
        )

    if len(content) > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise InferenceException(
            status_code=413,
            code=ErrorCode.FILE_TOO_LARGE,
            message=f"Uploaded VTK file exceeds the maximum size limit of {max_mb} MB.",
            model=model_name,
        )

    # Check for '# vtk DataFile Version' in the first 256 bytes
    header_sample = content[:256].lower()
    if b"# vtk datafile version" not in header_sample:
        raise InferenceException(
            status_code=422,
            code=ErrorCode.INVALID_VTK,
            message="Invalid or corrupted VTK file: missing valid VTK header signature ('# vtk DataFile Version').",
            model=model_name,
        )

    return filename, content, content_type
