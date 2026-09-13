"""
core/config.py — Centralized Application Configuration
========================================================
Uses Pydantic Settings (v2) to:
  1. Read all configuration from environment variables (12-Factor App principle).
  2. Validate and type-coerce values at startup — the application fails FAST
     with a clear error if a required environment variable is missing.
  3. Provide a single `get_settings()` function (cached) used everywhere via
     FastAPI's dependency injection system.

WHY PYDANTIC SETTINGS?
  - In production, secrets (DB password, MQTT credentials) must NEVER be
    hardcoded. Pydantic Settings enforces this pattern.
  - Type validation catches misconfiguration early — e.g., if someone sets
    MQTT_PORT="abc", the app won't start instead of crashing later.
  - lru_cache ensures the Settings object is constructed only once.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Precedence (highest to lowest):
      1. Environment variables (ideal for production/Docker)
      2. .env file in the project root (for local development)
      3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars to avoid noisy errors
    )

    # -------------------------------------------------------------------------
    # Application Identity
    # -------------------------------------------------------------------------
    APP_NAME: str = "ForgePulse"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="development", description="development | staging | production")
    DEBUG: bool = Field(default=True)

    # -------------------------------------------------------------------------
    # Database Configuration
    # In Docker Compose: POSTGRES_HOST=postgres (service name)
    # In production (Render): POSTGRES_URL is provided as a full connection string
    # -------------------------------------------------------------------------
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL hostname")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="forgepulse", description="Database name")
    POSTGRES_USER: str = Field(default="forgepulse_user", description="Database user")
    POSTGRES_PASSWORD: str = Field(default="forgepulse_pass", description="Database password")

    # Optional full DATABASE_URL override (Render provides this as a single string)
    DATABASE_URL: str | None = Field(default=None)

    # Connection pool settings
    DB_POOL_SIZE: int = Field(default=5, description="SQLAlchemy pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="SQLAlchemy max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Seconds to wait for a connection")

    # -------------------------------------------------------------------------
    # MQTT Broker Configuration
    # Local: Mosquitto in Docker Compose (host: mosquitto, port: 1883)
    # Production: HiveMQ Cloud or EMQX Cloud (configured via environment vars)
    # -------------------------------------------------------------------------
    MQTT_BROKER_HOST: str = Field(default="localhost", description="MQTT broker hostname")
    MQTT_BROKER_PORT: int = Field(default=1883, description="MQTT broker port (1883=plain, 8883=TLS)")
    MQTT_CLIENT_ID: str = Field(default="forgepulse-backend", description="Unique MQTT client identifier")
    MQTT_USERNAME: str | None = Field(default=None, description="MQTT broker username")
    MQTT_PASSWORD: str | None = Field(default=None, description="MQTT broker password")
    MQTT_USE_TLS: bool = Field(default=False, description="Enable TLS for cloud MQTT brokers")
    MQTT_KEEPALIVE: int = Field(default=60, description="Seconds between keepalive pings")

    # Topic pattern: factory/{plant_id}/{machine_id}/telemetry
    MQTT_TOPIC_PREFIX: str = Field(default="factory", description="Root topic prefix")

    # QoS Level explanation (documented here for interview reference):
    # QoS 0 = At most once (fire and forget) — fastest, no guarantee
    # QoS 1 = At least once (guaranteed delivery, possible duplicates) — WE USE THIS
    # QoS 2 = Exactly once (guaranteed, no duplicates) — slowest, overhead
    # We use QoS 1 because:
    #   - Telemetry loss is unacceptable for anomaly detection accuracy
    #   - Duplicate telemetry is acceptable (idempotent persistence)
    MQTT_QOS: int = Field(default=1, description="MQTT Quality of Service level (0, 1, or 2)")

    # -------------------------------------------------------------------------
    # Alert Engine Configuration
    # -------------------------------------------------------------------------
    ALERT_COOLDOWN_SECONDS: int = Field(
        default=300,
        description="Seconds to suppress duplicate alerts of the same type per machine"
    )

    # -------------------------------------------------------------------------
    # Analytics / ML Configuration
    # -------------------------------------------------------------------------
    ANOMALY_ZSCORE_THRESHOLD: float = Field(
        default=3.0,
        description="Z-score magnitude above which a reading is flagged as anomalous"
    )
    TELEMETRY_WINDOW_SIZE: int = Field(
        default=50,
        description="Number of recent readings used for rolling statistical baseline"
    )

    # -------------------------------------------------------------------------
    # API Server
    # -------------------------------------------------------------------------
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)

    # CORS: Frontend origins allowed to call the API
    # In production, replace with exact Vercel domain
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins"
    )

    # -------------------------------------------------------------------------
    # Computed Properties
    # These are derived at runtime — not read from env variables
    # -------------------------------------------------------------------------
    @computed_field  # type: ignore[misc]
    @property
    def database_url_sync(self) -> str:
        """
        Synchronous SQLAlchemy connection URL.
        Used by Alembic migrations (which are synchronous by nature).
        If DATABASE_URL is set (e.g., by Render), parse and convert it.
        """
        if self.DATABASE_URL:
            # Render provides: postgresql://user:pass@host/db
            # Replace asyncpg scheme for sync usage:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            if url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
            return url
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def database_url_async(self) -> str:
        """
        Async SQLAlchemy connection URL using asyncpg driver.
        Used by the FastAPI application at runtime.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse the comma-separated CORS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        """Convenience flag for production-specific behavior."""
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using @lru_cache means Settings is constructed exactly ONCE per process.
    This is important because Pydantic validates all fields on construction —
    we don't want to re-read and re-validate environment variables on every
    API request.

    FastAPI Usage:
        from app.core.config import get_settings
        settings = Depends(get_settings)
    """
    return Settings()
