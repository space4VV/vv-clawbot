"""Configuration management using Pydantic v2."""

import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SlackSettings(BaseSettings):
    """Slack configuration."""

    bot_token: str = Field(default="", validation_alias="SLACK_BOT_TOKEN")
    app_token: str = Field(default="", validation_alias="SLACK_APP_TOKEN")
    user_token: str | None = Field(default=None, validation_alias="SLACK_USER_TOKEN")
    signing_secret: str | None = Field(default=None, validation_alias="SLACK_SIGNING_SECRET")

    model_config = SettingsConfigDict(env_prefix="SLACK_", populate_by_name=True)


class AISettings(BaseSettings):
    """AI provider configuration."""

    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    default_model: str = Field(default="claude-sonnet-4-20250514", validation_alias="DEFAULT_MODEL")

    model_config = SettingsConfigDict(env_prefix="AI_", populate_by_name=True)


class RagSettings(BaseSettings):
    """RAG (Retrieval Augmented Generation) configuration."""

    enabled: bool = Field(default=True, validation_alias="RAG_ENABLED")
    embedding_model: str = Field(
        default="text-embedding-3-small", validation_alias="RAG_EMBEDDING_MODEL"
    )
    vector_db_path: str = Field(default="./data/chroma", validation_alias="RAG_VECTOR_DB_PATH")
    index_interval_hours: int = Field(default=1, validation_alias="RAG_INDEX_INTERVAL_HOURS")
    max_results: int = Field(default=10, validation_alias="RAG_MAX_RESULTS")
    min_similarity: float = Field(default=0.5, validation_alias="RAG_MIN_SIMILARITY")

    model_config = SettingsConfigDict(env_prefix="RAG_")


class MemorySettings(BaseSettings):
    """Memory (mem0) configuration."""

    enabled: bool = Field(default=True, validation_alias="MEMORY_ENABLED")
    extraction_model: str = Field(default="gpt-4o-mini", validation_alias="MEMORY_EXTRACTION_MODEL")

    model_config = SettingsConfigDict(env_prefix="MEMORY_")


class AppSettings(BaseSettings):
    """Application settings."""

    log_level: str = Field(default="info", validation_alias="LOG_LEVEL")
    database_path: str = Field(default="./data/assistant.db", validation_alias="DATABASE_PATH")
    max_history_messages: int = Field(default=50, validation_alias="MAX_HISTORY_MESSAGES")
    session_timeout_minutes: int = Field(default=60, validation_alias="SESSION_TIMEOUT_MINUTES")

    model_config = SettingsConfigDict(env_prefix="APP_")


class SecuritySettings(BaseSettings):
    """Security settings for DM access control."""

    dm_policy: str = Field(default="pairing", validation_alias="DM_POLICY")
    allowed_users: list[str] = Field(default=["*"], validation_alias="ALLOWED_USERS")
    allowed_channels: list[str] = Field(default=["*"], validation_alias="ALLOWED_CHANNELS")

    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    @field_validator("allowed_users", "allowed_channels", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated string from env to list."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()] if v else ["*"]
        return ["*"]

    @property
    def parse_allowed_users(self) -> list[str]:
        """Get effective allowed users list."""
        if not self.allowed_users or self.allowed_users == ["*"]:
            return ["*"]
        return self.allowed_users


class FeaturesSettings(BaseSettings):
    """Feature flags."""

    thread_summary: bool = Field(default=True, validation_alias="ENABLE_THREAD_SUMMARY")
    task_scheduler: bool = Field(default=True, validation_alias="ENABLE_TASK_SCHEDULER")
    reactions: bool = Field(default=True, validation_alias="ENABLE_REACTIONS")
    typing_indicator: bool = Field(default=True, validation_alias="ENABLE_TYPING_INDICATOR")

    model_config = SettingsConfigDict(env_prefix="ENABLE_")


class Settings(BaseSettings):
    """Main application settings combining all sub-settings."""

    slack: SlackSettings = Field(default_factory=SlackSettings)
    ai: AISettings = Field(default_factory=AISettings)
    rag: RagSettings = Field(default_factory=RagSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    app: AppSettings = Field(default_factory=AppSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    features: FeaturesSettings = Field(default_factory=FeaturesSettings)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def validate_config(self) -> None:
        """Validate that at least one AI provider is configured."""
        if not self.ai.anthropic_api_key and not self.ai.openai_api_key:
            msg = "At least one AI provider (Anthropic or OpenAI) must be configured"
            raise ValueError(msg)


# Global settings instance - validation deferred to avoid import errors in tests
settings = Settings()


def validate_settings() -> None:
    """Validate settings that require API keys. Call this before starting the app."""
    settings.validate_config()


def _should_validate_on_import() -> bool:
    """Check if we should validate settings at import time (skip in tests)."""
    if os.environ.get("SLACK_AI_SKIP_VALIDATION") == "1":
        return False
    return bool(
        os.environ.get("SLACK_BOT_TOKEN")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )


if _should_validate_on_import():
    validate_settings()
