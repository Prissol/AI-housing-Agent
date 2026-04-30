from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0


class OCRBlock(BaseModel):
    text: str
    bbox: BBox
    confidence: float = 0.0
    tile_id: str


class NamedSpatialItem(BaseModel):
    name: Optional[str] = None
    count: Optional[int] = None
    area_sqft: Optional[float] = None
    width_ft: Optional[float] = None
    bbox: Optional[BBox] = None
    floor: Optional[str] = None
    geometry_ref: Optional[Dict[str, Any]] = None
    source_trace: Optional[Dict[str, Any]] = None


class DimensionItem(BaseModel):
    label: str
    value: Optional[float] = None
    unit: str = "ft"
    bbox: Optional[BBox] = None
    source: str = "ocr_vision"
    source_trace: Optional[Dict[str, Any]] = None


class ConfidenceBreakdown(BaseModel):
    floors: float = 0.0
    rooms: float = 0.0
    circulation: float = 0.0
    dimensions: float = 0.0


class ExtractedDocument(BaseModel):
    analysis_id: str
    source_file: str
    drawing_id: Optional[str] = None
    units_detected: List[str] = Field(default_factory=list)
    scale_info: Dict[str, Any] = Field(default_factory=dict)
    ocr_blocks: List[OCRBlock] = Field(default_factory=list)
    floors: List[NamedSpatialItem] = Field(default_factory=list)
    rooms: List[NamedSpatialItem] = Field(default_factory=list)
    stairs: List[NamedSpatialItem] = Field(default_factory=list)
    lifts: List[NamedSpatialItem] = Field(default_factory=list)
    exits: List[NamedSpatialItem] = Field(default_factory=list)
    corridors: List[NamedSpatialItem] = Field(default_factory=list)
    dimensions: List[DimensionItem] = Field(default_factory=list)
    confidence: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    unresolved_fields: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
