from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRETS = frozenset(
    {
        "business-os-dev-secret",
        "business-os-worker-secret",
        "change-me",
        "changeme",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "business_os"
    postgres_password: str = "business_os_dev"
    postgres_db: str = "business_os"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "business-os"
    minio_secure: bool = False

    storage_backend: str = "local"
    local_storage_path: str = "./.data/storage"

    auth_required: bool = False
    auth_secret: str = "business-os-dev-secret"
    auth_token_ttl_seconds: int = 60 * 60 * 12
    worker_secret: str = "business-os-worker-secret"
    bootstrap_admin_password: str = "demo-admin"
    bootstrap_enabled: bool = True

    # Comma-separated origins. Empty = allow localhost web ports only.
    cors_origins: str = "http://localhost:3010,http://localhost:3000"
    docs_enabled: bool = True
    # 0 disables rate limiting (tests). Pilot: 20–60.
    rate_limit_per_minute: int = 0
    # When true: refuse startup if AUTH_REQUIRED with default secrets.
    pilot_mode: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    @property
    def postgres_dsn(self) -> str:
        password = quote_plus(self.postgres_password)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "").strip()
        if not raw or raw == "*":
            return ["http://localhost:3010", "http://localhost:3000"]
        return [part.strip() for part in raw.split(",") if part.strip()]

    def secrets_are_insecure(self) -> bool:
        return self.auth_secret in INSECURE_SECRETS or self.worker_secret in INSECURE_SECRETS


@lru_cache
def get_settings() -> Settings:
    return Settings()
