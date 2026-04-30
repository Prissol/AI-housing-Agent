from fastapi import APIRouter, File, HTTPException, UploadFile, status

from schemas.analyze import AnalyzeMapResponse, BatchAnalyzeResponse, UnifiedAnalyzeResponse
from services.ai_analyzer import analyze_housing_map
from services.file_processor import (
    ALL_SUPPORTED_EXTENSIONS,
    process_mixed_files,
)
from services.image_processor import process_uploaded_images
from utils.config import settings
from utils.logger import get_logger
from utils.validators import (
    get_file_extension,
    validate_upload_content_size,
    validate_upload_file_meta,
)

router = APIRouter(tags=["Map Analysis"])
logger = get_logger(__name__)


@router.post("/analyze-map", response_model=AnalyzeMapResponse)
async def analyze_map(image: UploadFile = File(...)) -> AnalyzeMapResponse:
    validate_upload_file_meta(image)

    image_bytes = await image.read()
    validate_upload_content_size(image_bytes)

    logger.info("Analyzing image: %s (%s bytes)", image.filename, len(image_bytes))

    try:
        result = analyze_housing_map(
            image_bytes=image_bytes,
            filename=image.filename or "",
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive catch for API stability
        logger.exception("Unexpected map analysis error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze map. Please try again.",
        ) from exc


@router.post("/analyze-maps", response_model=BatchAnalyzeResponse)
async def analyze_maps(files: list[UploadFile] = File(...)) -> BatchAnalyzeResponse:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload at least one image file.",
        )
    if len(files) > settings.batch_max_files:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Too many files in one batch. Maximum allowed is {settings.batch_max_files}."
            ),
        )

    logger.info("Batch analysis started for %s files.", len(files))

    try:
        return await process_uploaded_images(files)
    except Exception as exc:  # pragma: no cover - defensive catch for API stability
        logger.exception("Unexpected batch analysis error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch analysis failed. Please try again.",
        ) from exc


@router.post("/analyze-files", response_model=UnifiedAnalyzeResponse)
async def analyze_files(files: list[UploadFile] = File(...)) -> UnifiedAnalyzeResponse:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload at least one file.",
        )
    if len(files) > settings.unified_max_files:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Too many files. Maximum allowed is {settings.unified_max_files}.",
        )

    unsupported = []
    for file in files:
        extension = get_file_extension(file.filename)
        if extension not in ALL_SUPPORTED_EXTENSIONS:
            unsupported.append(file.filename or "unknown")

    if unsupported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file types detected: "
                + ", ".join(unsupported)
                + ". Allowed: .jpg, .jpeg, .png, .pdf, .xlsx, .csv."
            ),
        )

    logger.info("Unified analysis started for %s files.", len(files))
    try:
        return await process_mixed_files(files)
    except Exception as exc:  # pragma: no cover
        logger.exception("Unified analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze files.",
        ) from exc
