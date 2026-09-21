"""Configuracion de la aplicacion, leida desde variables de entorno."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


def _config(prefix: str = "") -> SettingsConfigDict:
    """Configuracion comun de lectura de entorno, con el prefijo de cada bloque."""
    return SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        env_prefix=prefix,
    )


class AppSettings(BaseSettings):
    model_config = _config("APP_")

    env: Environment = Environment.DEVELOPMENT
    debug: bool = False
    cors_origins: list[str] = Field(default_factory=list)

    @property
    def is_production(self) -> bool:
        return self.env is Environment.PRODUCTION


class DatabaseSettings(BaseSettings):
    model_config = _config("DATABASE_")

    url: SecretStr
    pool_min_size: int = 2
    pool_max_size: int = 10
    command_timeout: float = 30.0
    # El Transaction Pooler de Supabase (puerto 6543) no mantiene la misma
    # conexion entre sentencias, asi que las preparadas fallan. Ahi va en 0.
    statement_cache_size: int = 100


class SupabaseSettings(BaseSettings):
    model_config = _config("SUPABASE_")

    url: str
    project_ref: str
    service_role_key: SecretStr
    synthetic_email_domain: str = "buenpastor.app"
    jwt_audience: str = "authenticated"
    jwks_cache_seconds: int = 3600

    @property
    def jwks_url(self) -> str:
        return f"{self.url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def admin_users_url(self) -> str:
        return f"{self.url.rstrip('/')}/auth/v1/admin/users"

    @property
    def issuer(self) -> str:
        return f"{self.url.rstrip('/')}/auth/v1"


class CloudinarySettings(BaseSettings):
    model_config = _config("CLOUDINARY_")

    cloud_name: str
    api_key: SecretStr
    api_secret: SecretStr
    upload_folder: str = "kingdom-core"


class ObservabilitySettings(BaseSettings):
    model_config = _config()

    log_level: str = "INFO"
    log_json: bool = False
    sentry_dsn: str = ""


class Settings:
    """Agrupa los bloques de configuracion en un solo objeto."""

    def __init__(self) -> None:
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.supabase = SupabaseSettings()
        self.cloudinary = CloudinarySettings()
        self.observability = ObservabilitySettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
