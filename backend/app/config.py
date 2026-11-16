import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = (BACKEND_DIR / "rankly.db").as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(BACKEND_DIR / ".env"), ".env"],
        extra="ignore",
    )
    app_name: str = "RankArc API"
    database_url: str = f"sqlite+aiosqlite:///{DB_PATH}"
    redis_url: str = "redis://localhost:6379/0"
    backend_cors_origins: str = "http://localhost:5173"

    # Auth
    secret_key: str = "changeme-in-production-use-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # AI
    anthropic_api_key: str = ""

    # Files
    upload_dir: str = str(BACKEND_DIR / "uploads")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
