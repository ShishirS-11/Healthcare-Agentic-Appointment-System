
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Healthcare Agentic Appointment System"
    app_version: str = "1.0.0"
    debug: bool = True

    # API
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    # Database
    database_url: str = "sqlite:///./data/healthcare.db"

    # PubMed
    pubmed_email: str | None = None

    # Security
    secret_key: str = "development-only-change-this-secret"
    access_token_expire_minutes: int = Field(default=30, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Return a cached application settings instance."""
    return Settings()


settings = get_settings()
