"""Pytest configuration."""

import os
import sys
from pathlib import Path

import pytest


# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set test environment variable before any imports
os.environ["SLACK_AI_SKIP_VALIDATION"] = "1"
os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"
os.environ["SLACK_APP_TOKEN"] = "xapp-test-token"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-api-key"
os.environ["OPENAI_API_KEY"] = "sk-test-openai-key"
os.environ["RAG_ENABLED"] = "true"
os.environ["MEMORY_ENABLED"] = "true"
os.environ["LOG_LEVEL"] = "debug"


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-test-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-api-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("MEMORY_ENABLED", "true")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    return monkeypatch