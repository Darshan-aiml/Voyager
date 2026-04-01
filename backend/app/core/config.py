from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Voyager Backend"
    api_version: str = "1.0.0"

    railradar_base_url: str = Field(default="https://railradar.p.rapidapi.com")
    railradar_search_path: str = Field(default="/search")
    railradar_api_key: str = Field(default="")
    railradar_api_host: str = Field(default="railradar.p.rapidapi.com")

    aviationstack_base_url: str = Field(default="http://api.aviationstack.com/v1")
    aviationstack_api_key: str = Field(default="")

    request_timeout_seconds: float = 15.0
    min_transfer_buffer_hours: int = 2

    reliability_train: float = 0.95
    reliability_flight: float = 0.8
    reliability_bus: float = 0.65

    score_weight_price: float = 0.5
    score_weight_duration: float = 0.3
    score_weight_reliability: float = 0.2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
