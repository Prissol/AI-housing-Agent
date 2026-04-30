import asyncio

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from schemas.analyze import UnifiedAnalyzeResponse
from services.excel_processor import process_excel_bytes
from services.image_processor import process_image_bytes
from services.pdf_processor import process_pdf_bytes
from utils.config import settings
from utils.logger import get_logger
from utils.validators import get_file_extension

logger = get_logger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSIONS = {".pdf"}
EXCEL_EXTENSIONS = {".xlsx", ".csv"}
ALL_SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS | EXCEL_EXTENSIONS


async def _process_file(
    upload: UploadFile,
    semaphore: asyncio.Semaphore,
) -> tuple[list, list, list]:
    filename = upload.filename or "unnamed-file"
    extension = get_file_extension(filename)

    async with semaphore:
        try:
            file_bytes = await upload.read()
            if extension in IMAGE_EXTENSIONS:
                image_result = await run_in_threadpool(process_image_bytes, filename, file_bytes)
                return [image_result], [], []
            if extension in PDF_EXTENSIONS:
                pdf_results = await run_in_threadpool(process_pdf_bytes, filename, file_bytes)
                return [], pdf_results, []
            if extension in EXCEL_EXTENSIONS:
                excel_results = await run_in_threadpool(process_excel_bytes, filename, file_bytes)
                return [], [], excel_results

            logger.warning("Unsupported file skipped: %s", filename)
            return [], [], []
        except Exception as exc:  # pragma: no cover
            logger.exception("Unified processing failed for %s: %s", filename, exc)
            return [], [], []


async def process_mixed_files(files: list[UploadFile]) -> UnifiedAnalyzeResponse:
    max_workers = max(1, settings.batch_concurrency)
    semaphore = asyncio.Semaphore(max_workers)

    tasks = [_process_file(upload=file, semaphore=semaphore) for file in files]
    chunks = await asyncio.gather(*tasks)

    images = []
    pdfs = []
    excels = []
    for image_chunk, pdf_chunk, excel_chunk in chunks:
        images.extend(image_chunk)
        pdfs.extend(pdf_chunk)
        excels.extend(excel_chunk)

    return UnifiedAnalyzeResponse(images=images, pdfs=pdfs, excels=excels)
