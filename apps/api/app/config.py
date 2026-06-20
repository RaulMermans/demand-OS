from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    app_name: str = "DemandOS API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./demandos_dev.db"

    # Pipeline state
    pipeline_seeded: bool = False
    pipeline_ready: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Connector selection: mock | csv | shopify
    active_connector: str = "mock"

    # Optional API key guard for write/control endpoints.
    # When set, all POST/PATCH mutation endpoints require:
    #   X-DemandOS-API-Key: <value>
    # Leave empty (default) to disable the guard in local dev.
    # Never commit a real key here — set via environment variable.
    demandos_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
