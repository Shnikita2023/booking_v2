"""Application settings loaded from the environment."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://booking:booking@db:5432/booking"
    log_level: str = "INFO"
    jwt_secret: str = "change-me"
    access_ttl_min: int = 15
    refresh_ttl_days: int = 14
    reservation_ttl_min: int = 15
    webhook_secret: str = "webhook-change-me"

    @model_validator(mode="after")
    def _validate_prod_secrets(self) -> "Settings":
        if self.app_env == "prod":
            if self.jwt_secret == "change-me" or len(self.jwt_secret) < 32:
                raise ValueError("jwt_secret must be set to a secure value (≥32 chars) in prod")
            if self.webhook_secret == "webhook-change-me" or len(self.webhook_secret) < 32:
                raise ValueError("webhook_secret must be set to a secure value (≥32 chars) in prod")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
