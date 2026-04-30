from __future__ import annotations

import re
from pathlib import Path

import pytesseract

from utils.logger import get_logger

logger = get_logger(__name__)

PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {".txt", ".md"}


def _extract_pdf_text(pdf_path: Path) -> str:
    text_parts: list[str] = []
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
    except Exception as exc:
        logger.warning("pdfplumber extraction failed for %s: %s", pdf_path, exc)

    text = "\n".join(text_parts).strip()
    if len(text) > 100:
        return text

    # Fallback to PyMuPDF if needed
    try:
        import fitz  # type: ignore

        doc = fitz.open(str(pdf_path))
        parts = [page.get_text("text") for page in doc]
        doc.close()
        text = "\n".join(parts).strip()
    except Exception as exc:
        logger.warning("PyMuPDF extraction failed for %s: %s", pdf_path, exc)
        text = ""

    return text


def _ocr_image_file(image_path: Path) -> str:
    try:
        from PIL import Image

        image = Image.open(image_path)
        return pytesseract.image_to_string(image)
    except Exception as exc:
        logger.warning("OCR failed for %s: %s", image_path, exc)
        return ""


def extract_bylaw_text(document_paths: list[Path]) -> str:
    text_chunks: list[str] = []
    for path in document_paths:
        ext = path.suffix.lower()
        if ext in PDF_EXTENSIONS:
            text_chunks.append(_extract_pdf_text(path))
        elif ext in TEXT_EXTENSIONS:
            try:
                text_chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            except Exception as exc:
                logger.warning("Text read failed for %s: %s", path, exc)
        elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
            text_chunks.append(_ocr_image_file(path))

    return "\n".join(chunk for chunk in text_chunks if chunk).strip()


def heuristically_structure_rules(bylaw_text: str) -> list[str]:
    """Extract practical rule strings from raw bylaws text."""
    if not bylaw_text:
        return []

    rules: list[str] = []
    text = re.sub(r"\s+", " ", bylaw_text)

    height_matches = re.findall(
        r"(?:max(?:imum)?\s+)?(?:building\s+)?height[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*(?:ft|feet)",
        text,
        flags=re.IGNORECASE,
    )
    for value in height_matches[:3]:
        numeric = float(value)
        if 20 <= numeric <= 300:
            rules.append(f"Building height must be <= {value} ft")

    road_matches = re.findall(
        r"(?:min(?:imum)?\s+)?road\s+width[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*(?:ft|feet)",
        text,
        flags=re.IGNORECASE,
    )
    for value in road_matches[:3]:
        numeric = float(value)
        if 8 <= numeric <= 200:
            rules.append(f"Road width must be >= {value} ft")

    if re.search(r"no\s+commercial[^.\n]{0,60}residential", text, flags=re.IGNORECASE):
        rules.append("No commercial building in residential zone")
    if re.search(r"setback", text, flags=re.IGNORECASE):
        rules.append("Setback rules must be satisfied as per plot category")
    if re.search(r"parking", text, flags=re.IGNORECASE):
        rules.append("Mandatory parking requirement must be satisfied")

    # Fallback short bullet-like lines
    lines = [line.strip(" -\t") for line in bylaw_text.splitlines() if len(line.strip()) > 20]
    for line in lines[:20]:
        if any(token in line.lower() for token in ["must", "minimum", "maximum", "not allowed", "required"]):
            rules.append(line)

    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for rule in rules:
        key = rule.lower()
        if key not in seen:
            if "height" in key:
                match = re.search(r"(\d+(?:\.\d+)?)", key)
                if match and float(match.group(1)) < 20:
                    continue
            if "road width" in key:
                match = re.search(r"(\d+(?:\.\d+)?)", key)
                if match and float(match.group(1)) < 8:
                    continue
            seen.add(key)
            deduped.append(rule)

    return deduped[:30]
