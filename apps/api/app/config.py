from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FITPLATE_", extra="ignore")

    ai_mode: str = "mock"
    ai_provider: str = "fake"
    ai_model: str = "gpt-5.4-mini"
    ai_provider_api_key: str | None = None
    monthly_cost_cap_usd: float = 0.0
    ai_request_timeout_seconds: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
