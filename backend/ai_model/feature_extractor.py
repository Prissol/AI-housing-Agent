from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class MapFeatures:
    width: int
    height: int
    edge_density: float
    line_count: int
    rectangle_count: int
    foreground_ratio: float
    sharpness_score: float
    contrast_score: float


def extract_map_features(image_bgr: np.ndarray) -> MapFeatures:
    height, width = image_bgr.shape[:2]

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    contrast_score = float(np.std(gray))
    sharpness_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    denoised = cv2.bilateralFilter(gray, d=7, sigmaColor=75, sigmaSpace=75)
    edges = cv2.Canny(denoised, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=70,
        minLineLength=max(25, width // 35),
        maxLineGap=10,
    )
    line_count = int(0 if lines is None else len(lines))

    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        8,
    )
    foreground_ratio = float(np.count_nonzero(binary)) / float(binary.size)

    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    rectangle_count = 0
    min_area = max(120, (width * height) * 0.00004)
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue

        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            rectangle_count += 1

    return MapFeatures(
        width=width,
        height=height,
        edge_density=edge_density,
        line_count=line_count,
        rectangle_count=rectangle_count,
        foreground_ratio=foreground_ratio,
        sharpness_score=sharpness_score,
        contrast_score=contrast_score,
    )
