import asyncio

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from schemas.analyze import (
    BatchAnalyzeItem,
    BatchAnalyzeResponse,
    BatchStatus,
    GroupedFileItem,
)
from services.ai_analyzer import analyze_housing_map
from utils.config import settings
from utils.logger import get_logger
from utils.validators import (
    validate_generic_file_size,
    validate_upload_content_size,
    validate_upload_file_meta,
)

logger = get_logger(__name__)

ALLOWED_BATCH_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_BATCH_CONTENT_TYPES = {"image/jpeg", "image/png"}


def process_image_bytes(filename: str, image_bytes: bytes) -> GroupedFileItem:
    try:
        validate_generic_file_size(image_bytes, "Image file")
        single_result = analyze_housing_map(
            image_bytes=image_bytes,
            filename=filename,
        )
        return GroupedFileItem(
            filename=filename,
            status=BatchStatus(single_result.status.value),
            details=single_result.details,
        )
    except HTTPException as exc:
        logger.warning("Image processing failed for %s: %s", filename, exc.detail)
        return GroupedFileItem(
            filename=filename,
            status=BatchStatus.FAILED,
            details="Image could not be analyzed.",
            error=str(exc.detail),
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected image processing error for %s: %s", filename, exc)
        return GroupedFileItem(
            filename=filename,
            status=BatchStatus.FAILED,
            details="Unexpected processing error for this image.",
            error="Unexpected server error.",
        )


async def _process_single_upload(
    image: UploadFile,
    semaphore: asyncio.Semaphore,
) -> BatchAnalyzeItem:
    filename = image.filename or "unnamed-file"

    async with semaphore:
        try:
            validate_upload_file_meta(
                image=image,
                allowed_extensions=ALLOWED_BATCH_EXTENSIONS,
                allowed_content_types=ALLOWED_BATCH_CONTENT_TYPES,
            )
            image_bytes = await image.read()
            validate_upload_content_size(image_bytes)

            single_result = await run_in_threadpool(
                analyze_housing_map,
                image_bytes,
                filename,
            )
            return BatchAnalyzeItem(
                filename=filename,
                status=BatchStatus(single_result.status.value),
                details=single_result.details,
                confidence=single_result.confidence,
                risk_score=single_result.risk_score,
            )
        except HTTPException as exc:
            logger.warning("File skipped: %s | reason: %s", filename, exc.detail)
            return BatchAnalyzeItem(
                filename=filename,
                status=BatchStatus.FAILED,
                details="Image could not be analyzed.",
                error=str(exc.detail),
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Unexpected error while processing %s: %s", filename, exc)
            return BatchAnalyzeItem(
                filename=filename,
                status=BatchStatus.FAILED,
                details="Unexpected processing error for this image.",
                error="Unexpected server error.",
            )


async def process_uploaded_images(files: list[UploadFile]) -> BatchAnalyzeResponse:
    max_workers = max(1, settings.batch_concurrency)
    semaphore = asyncio.Semaphore(max_workers)

    logger.info(
        "Batch processor running with concurrency=%s for %s files.",
        max_workers,
        len(files),
    )

    tasks = [_process_single_upload(image=image, semaphore=semaphore) for image in files]
    results = await asyncio.gather(*tasks)

    return BatchAnalyzeResponse(results=results)
