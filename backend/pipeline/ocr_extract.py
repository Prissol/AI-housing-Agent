from __future__ import annotations

from pathlib import Path
from typing import List
import re

import cv2
import pytesseract
from pytesseract import TesseractNotFoundError

from core.config import get_settings
from core.logger import get_logger
from pipeline.preprocess import Tile
from schemas.extracted import BBox, OCRBlock

logger = get_logger(__name__)


def _configure_tesseract_binary() -> None:
    settings = get_settings()
    if settings.tesseract_cmd.strip():
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd.strip()
        return

    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return


def extract_ocr_blocks(tiles: List[Tile]) -> List[OCRBlock]:
    settings = get_settings()
    _configure_tesseract_binary()
    blocks: List[OCRBlock] = []
    ocr_unavailable = False
    for tile in tiles:
        if settings.ocr_engine != "pytesseract":
            logger.warning("Only pytesseract is currently enabled in this implementation.")
        rgb = cv2.cvtColor(tile.image, cv2.COLOR_BGR2RGB)
        try:
            data = pytesseract.image_to_data(
                rgb,
                config="--oem 3 --psm 6",
                output_type=pytesseract.Output.DICT,
            )
        except TesseractNotFoundError:
            # Keep pipeline alive even when OCR runtime dependency is missing.
            if not ocr_unavailable:
                logger.warning("Tesseract is not installed/in PATH. Continuing with empty OCR blocks.")
                ocr_unavailable = True
            continue
        for idx, text in enumerate(data.get("text", [])):
            cleaned = str(text or "").strip()
            # Drop punctuation/noise fragments to reduce OCR_READ_ERROR pollution.
            if cleaned and re.fullmatch(r"[\W_]+", cleaned):
                continue
            if cleaned and len(cleaned) == 1 and not cleaned.isdigit():
                continue
            try:
                conf = float(data.get("conf", [0])[idx] or 0.0)
            except (ValueError, TypeError):
                conf = 0.0
            if not cleaned or conf < settings.ocr_min_confidence:
                continue
            x = float(data["left"][idx])
            y = float(data["top"][idx])
            w = float(data["width"][idx])
            h = float(data["height"][idx])
            blocks.append(
                OCRBlock(
                    text=cleaned,
                    confidence=max(0.0, conf / 100.0),
                    bbox=BBox(x=x, y=y, w=w, h=h),
                    tile_id=tile.tile_id,
                )
            )
    return blocks
