"""Centralised application configuration.

All runtime parameters are read from environment variables (or a local `.env`
file). Code outside this module must not read `os.environ` directly.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Defaults are tuned for local development against the bundled docker-compose
    stack. Override via environment variables or a `.env` file at the project
    root.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Runtime environment
    app_env: str = Field(default="local", description="Deployment environment label.")
    app_host: str = Field(default="0.0.0.0", description="HTTP bind host.")
    app_port: int = Field(default=8000, description="HTTP bind port.")
    app_log_level: str = Field(default="INFO", description="Uvicorn / app log level.")

    # PostgreSQL
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="flowdocs")
    postgres_user: str = Field(default="flowdocs")
    postgres_password: str
    postgres_schema: str = Field(default="public")

    # LLM Providers
    llm_provider: str = Field(
        default="gemini",
        description="The LLM provider to use (gemini, mock)."
    )
    
    gemini_api_key: str | None = Field(
        default=None,
        description="API key for Google Gemini."
    )
    gemini_model: str = Field(
        default="gemini-3.1-flash-lite",
        description="The Gemini model to use."
    )
    gemini_max_rpm: int = Field(
        default=10,
        description="Maximum Gemini API requests per minute globally."
    )
    gemini_max_retries: int = Field(
        default=3,
        description="Maximum retries for 429 quota errors."
    )
    gemini_initial_backoff_seconds: float = Field(
        default=5.0,
        description="Initial backoff seconds before retrying on 429."
    )
    llm_token_budget: int = Field(
        default=50000,
        description="Maximum allowed tokens per workflow run."
    )

    # Connection pool
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout: int = Field(default=30, ge=1)

    @property
    def database_url(self) -> str:
        """Build a SQLAlchemy URL using psycopg3.

        Passwords are URL-encoded so the resulting URL is safe even if a
        password contains reserved characters.
        """
        from urllib.parse import quote_plus

        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        host = self.postgres_host
        port = self.postgres_port
        db = self.postgres_db
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
