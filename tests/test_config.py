"""Tests for configuration module."""

import pytest
from pydantic import ValidationError

from clawbot_lib.config import (
    Settings,
    SlackSettings,
    AISettings,
    RagSettings,
    MemorySettings,
    AppSettings,
    SecuritySettings,
    FeaturesSettings,
)


class TestSlackSettings:
    """Test Slack settings validation."""

    def test_default_values(self, monkeypatch):
        """Test default values are set correctly."""
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.delenv("SLACK_APP_TOKEN", raising=False)
        settings = SlackSettings()
        assert settings.bot_token == ""
        assert settings.app_token == ""

    def test_env_variable_parsing(self):
        """Test environment variable parsing."""
        settings = SlackSettings(
            bot_token="xoxb-test-token",
            app_token="xapp-test-token",
        )
        assert settings.bot_token == "xoxb-test-token"
        assert settings.app_token == "xapp-test-token"


class TestAISettings:
    """Test AI settings validation."""

    def test_default_model(self):
        """Test default model is set."""
        settings = AISettings()
        assert settings.default_model == "claude-sonnet-4-20250514"

    def test_api_key_parsing(self):
        """Test API key parsing."""
        settings = AISettings(anthropic_api_key="sk-ant-test")
        assert settings.anthropic_api_key == "sk-ant-test"


class TestRagSettings:
    """Test RAG settings validation."""

    def test_defaults(self):
        """Test RAG defaults."""
        settings = RagSettings()
        assert settings.enabled is True
        assert settings.embedding_model == "text-embedding-3-small"
        assert settings.vector_db_path == "./data/chroma"
        assert settings.max_results == 10
        assert settings.min_similarity == 0.5


class TestMemorySettings:
    """Test memory settings."""

    def test_defaults(self):
        """Test memory defaults."""
        settings = MemorySettings()
        assert settings.enabled is True
        assert settings.extraction_model == "gpt-4o-mini"


class TestAppSettings:
    """Test app settings."""

    def test_defaults(self, monkeypatch):
        """Test app defaults."""
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        settings = AppSettings()
        assert settings.log_level == "info"
        assert settings.database_path == "./data/assistant.db"
        assert settings.max_history_messages == 50
        assert settings.session_timeout_minutes == 60


class TestSecuritySettings:
    """Test security settings."""

    def test_wildcard_allowed_users(self):
        """Test wildcard allowed users."""
        settings = SecuritySettings()
        assert "*" in settings.parse_allowed_users


class TestFeaturesSettings:
    """Test features settings."""

    def test_defaults(self):
        """Test feature defaults."""
        settings = FeaturesSettings()
        assert settings.thread_summary is True
        assert settings.task_scheduler is True
        assert settings.reactions is True
        assert settings.typing_indicator is True