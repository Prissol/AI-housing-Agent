from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    batch_max_files: int = Field(default=25, alias="BATCH_MAX_FILES")
    batch_concurrency: int = Field(default=4, alias="BATCH_CONCURRENCY")
    unified_max_files: int = Field(default=30, alias="UNIFIED_MAX_FILES")
    enforce_bylaw_evidence: bool = Field(default=False, alias="ENFORCE_BYLAW_EVIDENCE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allow_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",")]
        return [origin for origin in origins if origin]

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
