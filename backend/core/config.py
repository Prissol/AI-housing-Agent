from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Legal Maps Compliance API"
    app_env: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1", alias="OPENAI_MODEL")
    openai_max_retries: int = Field(default=3, alias="OPENAI_MAX_RETRIES")
    openai_retry_backoff_sec: float = Field(default=1.5, alias="OPENAI_RETRY_BACKOFF_SEC")
    max_tiles_per_page: int = Field(default=16, alias="MAX_TILES_PER_PAGE")
    ocr_engine: Literal["pytesseract", "easyocr"] = Field(default="pytesseract", alias="OCR_ENGINE")
    tesseract_cmd: str = Field(default="", alias="TESSERACT_CMD")
    ocr_min_confidence: float = Field(default=5.0, alias="OCR_MIN_CONFIDENCE")

    outputs_root: Path = Field(default=Path("outputs"))
    preprocessed_dir: Path = Field(default=Path("outputs/preprocessed"))
    extracted_dir: Path = Field(default=Path("outputs/extracted"))
    reports_dir: Path = Field(default=Path("outputs/reports"))
    bylaw_profiles_path: Path = Field(default=Path("rules/profiles.json"), alias="BYLAW_PROFILES_PATH")
    bylaw_db_path: Path = Field(default=Path("outputs/bylaws.db"), alias="BYLAW_DB_PATH")
    mongodb_uri: str = Field(default="", alias="MONGODB_URI")
    mongodb_db_name: str = Field(default="dha_ai_maps", alias="MONGODB_DB_NAME")
    mongodb_bylaws_collection: str = Field(default="bylaw_profiles", alias="MONGODB_BYLAWS_COLLECTION")
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    llama_endpoint: str = Field(default="", alias="LLAMA_ENDPOINT")
    max_upload_size_mb: int = Field(default=40, alias="MAX_UPLOAD_SIZE_MB")
    dwg_converter_path: str = Field(default="", alias="DWG_CONVERTER_PATH")
    dwg_temp_dir: Path = Field(default=Path("outputs/dwg_temp"), alias="DWG_TEMP_DIR")
    dwg_conversion_timeout_sec: int = Field(default=120, alias="DWG_CONVERSION_TIMEOUT_SEC")
    dwg_parse_confidence_threshold: float = Field(default=0.55, alias="DWG_PARSE_CONFIDENCE_THRESHOLD")
    cad_fast_mode: bool = Field(default=True, alias="CAD_FAST_MODE")
    cad_render_dpi: int = Field(default=150, alias="CAD_RENDER_DPI")
    confidence_threshold: float = Field(default=0.80, alias="CONFIDENCE_THRESHOLD")
    max_clarification_questions: int = Field(default=3, alias="MAX_CLARIFICATION_QUESTIONS")

    min_confidence_for_auto_pass: float = 0.75


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
