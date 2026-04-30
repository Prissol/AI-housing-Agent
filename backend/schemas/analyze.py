from enum import Enum

from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    VIOLATION = "Violation"
    NO_VIOLATION = "No Violation"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Finding(BaseModel):
    code: str
    title: str
    description: str
    severity: Severity


class AnalysisMetrics(BaseModel):
    width: int
    height: int
    edge_density: float = Field(ge=0.0, le=1.0)
    line_count: int = Field(ge=0)
    rectangle_count: int = Field(ge=0)
    foreground_ratio: float = Field(ge=0.0, le=1.0)
    sharpness_score: float = Field(ge=0.0)
    contrast_score: float = Field(ge=0.0)


class AnalyzeMapResponse(BaseModel):
    status: ComplianceStatus
    details: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    findings: list[Finding]
    metrics: AnalysisMetrics


class BatchStatus(str, Enum):
    VIOLATION = "Violation"
    NO_VIOLATION = "No Violation"
    FAILED = "Failed"


class BatchAnalyzeItem(BaseModel):
    filename: str
    status: BatchStatus
    details: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    error: str | None = None


class BatchAnalyzeResponse(BaseModel):
    results: list[BatchAnalyzeItem]


class GroupedFileItem(BaseModel):
    filename: str
    status: BatchStatus
    details: str
    error: str | None = None


class PdfPageResult(BaseModel):
    filename: str
    page: int
    status: BatchStatus
    details: str
    error: str | None = None


class ExcelRowResult(BaseModel):
    filename: str
    row: int
    status: BatchStatus
    details: str
    error: str | None = None


class UnifiedAnalyzeResponse(BaseModel):
    images: list[GroupedFileItem]
    pdfs: list[PdfPageResult]
    excels: list[ExcelRowResult]
