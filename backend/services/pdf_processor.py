import io

from fastapi import HTTPException
from pdf2image import convert_from_bytes

from schemas.analyze import BatchStatus, PdfPageResult
from services.ai_analyzer import analyze_housing_map
from utils.logger import get_logger
from utils.validators import validate_generic_file_size

logger = get_logger(__name__)


def process_pdf_bytes(filename: str, pdf_bytes: bytes) -> list[PdfPageResult]:
    try:
        validate_generic_file_size(pdf_bytes, "PDF file")
        pages = convert_from_bytes(pdf_bytes, fmt="jpeg")
        if not pages:
            return [
                PdfPageResult(
                    filename=filename,
                    page=1,
                    status=BatchStatus.FAILED,
                    details="PDF has no readable pages.",
                    error="No pages could be extracted.",
                )
            ]
    except HTTPException as exc:
        return [
            PdfPageResult(
                filename=filename,
                page=1,
                status=BatchStatus.FAILED,
                details="PDF could not be analyzed.",
                error=str(exc.detail),
            )
        ]
    except Exception as exc:
        logger.exception("PDF conversion failed for %s: %s", filename, exc)
        return [
            PdfPageResult(
                filename=filename,
                page=1,
                status=BatchStatus.FAILED,
                details="PDF could not be converted to pages.",
                error="Corrupted or unsupported PDF.",
            )
        ]

    results: list[PdfPageResult] = []
    for page_index, page_image in enumerate(pages, start=1):
        try:
            buffer = io.BytesIO()
            page_image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
            analysis = analyze_housing_map(image_bytes=image_bytes, filename=f"{filename}#page-{page_index}")
            results.append(
                PdfPageResult(
                    filename=filename,
                    page=page_index,
                    status=BatchStatus(analysis.status.value),
                    details=analysis.details,
                )
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("Page analysis failed for %s page %s: %s", filename, page_index, exc)
            results.append(
                PdfPageResult(
                    filename=filename,
                    page=page_index,
                    status=BatchStatus.FAILED,
                    details="PDF page could not be analyzed.",
                    error="Page processing failed.",
                )
            )
    return results
