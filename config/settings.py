from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")

    vault_path: Optional[Path] = Field(None, alias="VAULT_PATH")
    output_dir: Path = Field(Path("output"), alias="OUTPUT_DIR")

    scraper_timeout: int = Field(30000, alias="SCRAPER_TIMEOUT")
    scraper_max_pages: int = Field(30, alias="SCRAPER_MAX_PAGES")
    scraper_max_depth: int = Field(3, alias="SCRAPER_MAX_DEPTH")

    freelancer_day_rate: float = Field(800.0, alias="FREELANCER_DAY_RATE")

    audit_model: str = Field("claude-sonnet-4-6", alias="AUDIT_MODEL")
    reconstruct_model: str = Field("claude-haiku-4-5-20251001", alias="RECONSTRUCT_MODEL")

    def effective_vault_path(self) -> Path:
        if self.vault_path:
            return self.vault_path
        return self.output_dir / "vault"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
