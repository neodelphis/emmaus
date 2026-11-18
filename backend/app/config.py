from __future__ import annotations

from functools import lru_cache

from pydantic import EmailStr, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'API, lue dans l'environnement (et un éventuel .env local)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "local"
    database_url: str
    secret_key: SecretStr
    frontend_url: str = "http://localhost:8080"

    admin_email: EmailStr | None = None
    admin_password: SecretStr | None = None
    seed_admin: bool = True

    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_from: str = "Emmaus <ne-pas-repondre@emmaus.local>"
    smtp_timeout_seconds: int = 5

    session_hours: int = 12
    cookie_secure: bool = False
    reset_token_minutes: int = 60
    password_min_length: int = Field(default=12, ge=8)

    @field_validator("frontend_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("secret_key")
    @classmethod
    def _secret_key_long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("SECRET_KEY doit contenir au moins 32 caractères.")
        return value

    @property
    def secret(self) -> str:
        return self.secret_key.get_secret_value()

    def validate_bootstrap_credentials(self) -> None:
        """Vérifie la cohérence de la configuration du premier administrateur."""
        if self.admin_email is None and self.admin_password is None:
            return
        if self.admin_email is None or self.admin_password is None:
            raise RuntimeError(
                "ADMIN_EMAIL et ADMIN_PASSWORD doivent être définis ensemble."
            )
        if len(self.admin_password.get_secret_value()) < self.password_min_length:
            raise RuntimeError(
                f"ADMIN_PASSWORD doit contenir au moins {self.password_min_length} caractères."
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]
    settings.validate_bootstrap_credentials()
    return settings
