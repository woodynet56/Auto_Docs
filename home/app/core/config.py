"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets are never represented as plain strings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_NAME: str = "Gestoría Reaver"
    APP_ENV: Literal["development", "test", "staging", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    DATABASE_URL: SecretStr = Field(
        default=SecretStr("postgresql+psycopg://postgres:postgres@localhost:5432/gestoria_reaver")
    )
    DB_CONNECT_TIMEOUT_SECONDS: int = Field(default=5, ge=1, le=30)
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    PUBLIC_WHATSAPP_NUMBER: str | None = None
    WHATSAPP_INITIAL_MESSAGE: str = "Hola, quiero iniciar una solicitud con Gestoría Reaver."
    WA_VERIFY_TOKEN: SecretStr = Field(default=SecretStr(""))
    WA_APP_SECRET: SecretStr = Field(default=SecretStr(""))
    WA_PHONE_NUMBER_ID: str | None = None
    WA_BUSINESS_PHONE_NUMBER: str | None = None
    WA_ACCESS_TOKEN: SecretStr = Field(default=SecretStr(""))
    WA_API_VERSION: str = "v23.0"
    GESTOR_PHONE_NUMBER: str | None = None
    IDENTIFIER_ENCRYPTION_KEY: SecretStr = Field(default=SecretStr(""))
    IDENTIFIER_HASH_KEY: SecretStr = Field(default=SecretStr(""))
    META_HTTP_TIMEOUT_SECONDS: int = Field(default=10, ge=1, le=30)
    META_MAX_RETRIES: int = Field(default=2, ge=0, le=3)
    WEBHOOK_MAX_BODY_BYTES: int = Field(default=1_048_576, ge=1024, le=5_242_880)
    DOCUMENT_MAX_BYTES: int = Field(default=10_485_760, ge=1024, le=20_971_520)
    DOCUMENT_RETENTION_DAYS: int = Field(default=30, ge=1, le=365)
    R2_ENDPOINT_URL: str | None = None
    R2_BUCKET_NAME: str | None = None
    R2_ACCESS_KEY_ID: SecretStr = Field(default=SecretStr(""))
    R2_SECRET_ACCESS_KEY: SecretStr = Field(default=SecretStr(""))
    DELIVERY_LINK_TTL_SECONDS: int = Field(default=600, ge=60, le=900)
    DELIVERY_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=5)
    PORTAL_SESSION_TTL_MINUTES: int = Field(default=30, ge=5, le=1440)
    PORTAL_COOKIE_SECURE: bool = True
    PORTAL_OTP_MAX_ATTEMPTS: int = Field(default=5, ge=3, le=10)
    PORTAL_OTP_LOCK_MINUTES: int = Field(default=15, ge=5, le=60)
    CLAMAV_HOST: str | None = None
    CLAMAV_PORT: int = Field(default=3310, ge=1, le=65535)
    CLAMAV_TIMEOUT_SECONDS: int = Field(default=30, ge=1, le=120)
    MALWARE_SCAN_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    ADMIN_API_TOKEN: SecretStr = Field(default=SecretStr(""))

    @field_validator("PUBLIC_WHATSAPP_NUMBER")
    @classmethod
    def validate_public_whatsapp_number(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not value.isascii() or not value.isdigit() or not 8 <= len(value) <= 15:
            raise ValueError("PUBLIC_WHATSAPP_NUMBER must contain 8 to 15 ASCII digits")
        return value

    @field_validator("GESTOR_PHONE_NUMBER", "WA_BUSINESS_PHONE_NUMBER")
    @classmethod
    def validate_gestor_phone_number(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        normalized = value if value.startswith("+") else f"+{value}"
        if not normalized[1:].isascii() or not normalized[1:].isdigit():
            raise ValueError("Phone number must be an E.164 phone number")
        if not 8 <= len(normalized[1:]) <= 15 or normalized[1] == "0":
            raise ValueError("Phone number must be an E.164 phone number")
        return normalized

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_scheme(cls, value: SecretStr) -> SecretStr:
        url = value.get_secret_value()
        allowed = ("postgresql+psycopg://", "postgresql://")
        if not url.startswith(allowed):
            raise ValueError("DATABASE_URL must use PostgreSQL")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings object."""
    return Settings()
