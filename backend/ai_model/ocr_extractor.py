import re
from os import getenv
from pathlib import Path

import cv2

from utils.logger import get_logger

logger = get_logger(__name__)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def extract_ocr_text(image_bgr) -> tuple[str, str | None]:
    """
    Extract text from a plan image using pytesseract when available.

    Returns:
        (text, issue_code)
        - text: OCR output (possibly empty)
        - issue_code: None on success path, else a short reason
    """
    try:
        import pytesseract  # type: ignore
        from pytesseract import TesseractNotFoundError  # type: ignore
    except Exception:
        return "", "OCR_ENGINE_UNAVAILABLE"

    configured_cmd = getenv("TESSERACT_CMD", "").strip()
    default_cmd = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
    if configured_cmd:
        pytesseract.pytesseract.tesseract_cmd = configured_cmd
    elif default_cmd.exists():
        pytesseract.pytesseract.tesseract_cmd = str(default_cmd)

    try:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=15)
        upscaled = cv2.resize(denoised, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
        binary = cv2.adaptiveThreshold(
            upscaled,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        _, otsu = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        configs = ["--oem 3 --psm 6", "--oem 3 --psm 11", "--oem 3 --psm 12"]
        candidates: list[str] = []
        for config in configs:
            candidates.append(_normalize_whitespace(pytesseract.image_to_string(upscaled, config=config)))
            candidates.append(_normalize_whitespace(pytesseract.image_to_string(binary, config=config)))
            candidates.append(_normalize_whitespace(pytesseract.image_to_string(otsu, config=config)))

        best = max(candidates, key=len, default="")
        if not best:
            return "", "OCR_TEXT_EMPTY"
        return best, None
    except TesseractNotFoundError:
        return "", "OCR_BINARY_NOT_FOUND"
    except Exception as exc:  # pragma: no cover - external OCR guard
        message = str(exc).lower()
        if "tesseract is not installed" in message or "not in your path" in message:
            return "", "OCR_BINARY_NOT_FOUND"
        logger.warning("OCR extraction failed: %s", exc)
        return "", "OCR_FAILED"
