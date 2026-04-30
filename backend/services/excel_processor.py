import io

import pandas as pd

from schemas.analyze import BatchStatus, ExcelRowResult
from utils.logger import get_logger
from utils.validators import validate_generic_file_size

logger = get_logger(__name__)


def _to_float(value) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _evaluate_row(row: pd.Series) -> tuple[BatchStatus, str]:
    road_width = _to_float(row.get("road_width"))
    building_height = _to_float(row.get("building_height"))
    required_road_width = _to_float(row.get("required_road_width")) or 30.0
    max_building_height = _to_float(row.get("max_building_height")) or 40.0

    issues: list[str] = []
    if road_width is not None and road_width < required_road_width:
        issues.append(f"Road width too small ({road_width} < {required_road_width}).")
    if building_height is not None and building_height > max_building_height:
        issues.append(
            f"Building height exceeds limit ({building_height} > {max_building_height})."
        )

    if issues:
        return BatchStatus.VIOLATION, " ".join(issues)
    return BatchStatus.NO_VIOLATION, "Row passes basic bylaw checks."


def process_excel_bytes(filename: str, file_bytes: bytes) -> list[ExcelRowResult]:
    try:
        validate_generic_file_size(file_bytes, "Spreadsheet file")
        lower_name = filename.lower()
        if lower_name.endswith(".csv"):
            dataframe = pd.read_csv(io.BytesIO(file_bytes))
        else:
            dataframe = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception as exc:
        logger.exception("Spreadsheet read failed for %s: %s", filename, exc)
        return [
            ExcelRowResult(
                filename=filename,
                row=1,
                status=BatchStatus.FAILED,
                details="Spreadsheet could not be read.",
                error="Corrupted or unsupported excel/csv file.",
            )
        ]

    if dataframe.empty:
        return [
            ExcelRowResult(
                filename=filename,
                row=1,
                status=BatchStatus.FAILED,
                details="Spreadsheet has no rows.",
                error="No data found.",
            )
        ]

    results: list[ExcelRowResult] = []
    for index, row in dataframe.iterrows():
        status, details = _evaluate_row(row)
        results.append(
            ExcelRowResult(
                filename=filename,
                row=int(index + 1),
                status=status,
                details=details,
            )
        )
    return results
