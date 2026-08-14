"""Tests for application settings and environment variable loading."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_loads_postgres_password_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that settings correctly loads POSTGRES_PASSWORD from the environment."""
    monkeypatch.setenv("POSTGRES_PASSWORD", "custom_test_env_password_123")
    
    # We instantiate a fresh Settings object to bypass the lru_cache in get_settings
    settings = Settings()
    
    assert settings.postgres_password == "custom_test_env_password_123"
    assert "custom_test_env_password_123" in settings.database_url


def test_settings_url_encodes_postgres_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that postgres_password containing special characters is URL-encoded in database_url."""
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass/word@123#")
    
    settings = Settings()
    
    assert settings.postgres_password == "pass/word@123#"
    # "pass/word@123#" should encode to "pass%2Fword%40123%23"
    assert "pass%2Fword%40123%23" in settings.database_url
    assert "pass/word" not in settings.database_url


def test_settings_raises_error_if_password_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that Settings raises a validation error if POSTGRES_PASSWORD is not set.
    
    We subclass Settings to prevent it from loading from a local .env file
    during tests to prove the validation behavior when no source is available.
    """
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    
    class TestSettings(Settings):
        model_config = {
            **Settings.model_config,
            "env_file": None,  # Disable loading from .env file
        }

    with pytest.raises(ValidationError) as exc_info:
        TestSettings()
        
    assert "postgres_password" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)
