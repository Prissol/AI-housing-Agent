from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import fitz
import numpy as np
import pytesseract
from PIL import Image
from pytesseract import TesseractNotFoundError

from core.config import get_settings
from services.storage import ensure_output_dirs


@dataclass
class Tile:
    tile_id: str
    image: np.ndarray
    coords: Tuple[int, int, int, int]
    path: Path
    page_index: int = 0


def _deskew(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    angle = None
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=120, minLineLength=150, maxLineGap=20)
    if lines is not None and len(lines) > 0:
        candidate_angles: list[float] = []
        for line in lines[:, 0]:
            x1, y1, x2, y2 = line
            deg = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Normalize to near-horizontal angle range for deskew.
            if deg > 45:
                deg -= 90
            elif deg < -45:
                deg += 90
            if -30 <= deg <= 30:
                candidate_angles.append(float(deg))
        if candidate_angles:
            angle = float(np.median(candidate_angles))

    if angle is None:
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if coords.size == 0:
            return image
        rect_angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + rect_angle) if rect_angle < -45 else -rect_angle

    # Ignore tiny corrections to avoid over-rotating clean plans.
    if abs(angle) < 0.25:
        return image

    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _auto_orient(image: np.ndarray) -> np.ndarray:
    """
    Rotate image by coarse orientation (0/90/180/270) when detectable.
    This complements deskew, which handles smaller tilt angles.
    """
    try:
        osd = pytesseract.image_to_osd(image)
    except (TesseractNotFoundError, RuntimeError, ValueError):
        return image

    rotate = 0
    for line in osd.splitlines():
        if line.lower().startswith("rotate:"):
            raw = line.split(":", 1)[-1].strip()
            try:
                rotate = int(raw)
            except ValueError:
                rotate = 0
            break

    if rotate == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if rotate == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if rotate == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def _enhance(image: np.ndarray) -> np.ndarray:
    denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((l2, a, b)), cv2.COLOR_LAB2BGR)


def _rotate_by_degrees(image: np.ndarray, degrees: float) -> np.ndarray:
    normalized = ((degrees % 360) + 360) % 360
    if abs(normalized) < 0.01:
        return image

    h, w = image.shape[:2]
    center = (w / 2, h / 2)
    matrix = cv2.getRotationMatrix2D(center, -normalized, 1.0)
    cos = abs(matrix[0, 0])
    sin = abs(matrix[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    matrix[0, 2] += (new_w / 2) - center[0]
    matrix[1, 2] += (new_h / 2) - center[1]
    return cv2.warpAffine(image, matrix, (new_w, new_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _tile(image: np.ndarray, base_name: str, analysis_id: str, page_index: int = 0) -> List[Tile]:
    settings = get_settings()
    h, w = image.shape[:2]
    tile_size = 1400
    stride = 1100
    tiles: List[Tile] = []
    tile_count = 0
    ensure_output_dirs()
    for y in range(0, h, stride):
        for x in range(0, w, stride):
            x2 = min(x + tile_size, w)
            y2 = min(y + tile_size, h)
            crop = image[y:y2, x:x2]
            tile_id = f"{base_name}_p{page_index}_tile_{tile_count}"
            tile_path = settings.preprocessed_dir / f"{analysis_id}_{tile_id}.png"
            cv2.imwrite(str(tile_path), crop)
            tiles.append(Tile(tile_id=tile_id, image=crop, coords=(x, y, x2, y2), path=tile_path, page_index=page_index))
            tile_count += 1
            if tile_count >= settings.max_tiles_per_page:
                return tiles
    return tiles


def _preprocess_array(
    image: np.ndarray, file_stem: str, analysis_id: str, page_index: int = 0, manual_rotation_deg: float = 0
) -> List[Tile]:
    rotated = _rotate_by_degrees(image, manual_rotation_deg)
    resized = cv2.resize(rotated, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_CUBIC)
    oriented = _auto_orient(resized)
    cleaned = _enhance(_deskew(oriented))
    return _tile(cleaned, file_stem, analysis_id, page_index=page_index)


def preprocess_image(file_path: Path, analysis_id: str, manual_rotation_deg: float = 0) -> List[Tile]:
    image = cv2.imread(str(file_path))
    if image is None:
        pil = Image.open(file_path).convert("RGB")
        image = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return _preprocess_array(image, file_path.stem, analysis_id, page_index=0, manual_rotation_deg=manual_rotation_deg)


def preprocess_document(file_path: Path, analysis_id: str, manual_rotation_deg: float = 0) -> List[Tile]:
    if file_path.suffix.lower() != ".pdf":
        return preprocess_image(file_path, analysis_id, manual_rotation_deg=manual_rotation_deg)

    all_tiles: List[Tile] = []
    doc = fitz.open(file_path)
    settings = get_settings()
    for page_index, page in enumerate(doc):
        if len(all_tiles) >= settings.max_tiles_per_page:
            break
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        else:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        page_tiles = _preprocess_array(
            image, file_path.stem, analysis_id, page_index=page_index, manual_rotation_deg=manual_rotation_deg
        )
        all_tiles.extend(page_tiles)
    doc.close()
    return all_tiles[: settings.max_tiles_per_page]
