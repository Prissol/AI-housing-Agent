from pathlib import Path

from fastapi import HTTPException, UploadFile, status

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MIN_WIDTH = 500
MIN_HEIGHT = 500
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


def get_file_extension(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def validate_file_extension(filename: str | None, allowed_extensions: set[str]) -> None:
    extension = get_file_extension(filename)
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {extension or 'unknown'}.",
        )


def validate_upload_file_meta(
    image: UploadFile,
    allowed_extensions: set[str] | None = None,
    allowed_content_types: set[str] | None = None,
) -> None:
    final_extensions = allowed_extensions or ALLOWED_EXTENSIONS
    final_content_types = allowed_content_types or ALLOWED_CONTENT_TYPES

    if image.content_type is None or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed.",
        )
    if image.content_type.lower() not in final_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported image content type. "
                f"Allowed: {', '.join(sorted(final_content_types))}."
            ),
        )

    filename = image.filename or ""
    extension = Path(filename).suffix.lower()
    if extension and extension not in final_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file extension. "
                f"Use: {', '.join(sorted(final_extensions))}."
            ),
        )


def validate_upload_content_size(image_bytes: bytes) -> None:
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image is too large. Max allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
        )


def validate_generic_file_size(file_bytes: bytes, file_label: str = "File") -> None:
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{file_label} is empty.",
        )
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{file_label} is too large. Max allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
        )
