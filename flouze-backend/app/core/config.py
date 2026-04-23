from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://flouze:flouze@db:5432/flouze"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # JWT
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # OAuth2
    google_client_id: str = ""
    google_client_secret: str = ""

    # Exchange rates
    exchangerate_api_key: str = ""

    # CORS
    cors_origins: List[str] = ["http://localhost", "http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        return v

    # Exports
    export_dir: str = "/app/exports"

    # App
    debug: bool = False
    budget_alert_threshold: float = 0.80


settings = Settings()
