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

    # Runtime mode — controls filesystem and DB behaviour.
    # "local"  : default; SQLite fallback allowed; artifact files written to disk.
    # "vercel" : serverless; Postgres required; artifact files written to /tmp only.
    demandos_runtime_mode: str = "local"

    # Demo dataset scale — controls pipeline seed size.
    # "full"  : 50 products, 5 stores, 730 days (default for local dev).
    # "small" : 10 products, 2 stores, 180 days (recommended for Vercel to avoid timeouts).
    demandos_demo_scale: str = "full"


@lru_cache
def get_settings() -> Settings:
    return Settings()
