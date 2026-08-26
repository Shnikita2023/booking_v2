from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
