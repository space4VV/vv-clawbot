"""Tests for RAG module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from clawbot_lib.rag import (
    should_use_rag,
    build_context_string,
    parse_query_filters,
    RagDocument,
)


class TestShouldUseRag:
    """Test RAG trigger detection."""

    @pytest.mark.parametrize(
        "query,expected",
        [
            ("what was discussed", True),
            ("do you remember", True),
            ("earlier we talked about", True),
            ("show me the code", False),
            ("hello there", False),
            ("create a new file", False),
        ],
    )
    def test_rag_triggers(self, query: str, expected: bool):
        """Test various queries for RAG triggers."""
        assert should_use_rag(query) == expected


class TestBuildContextString:
    """Test context string building."""

    def test_empty_results(self):
        """Test with empty results."""
        result = build_context_string([])
        assert result == ""

    def test_single_result(self):
        """Test with single result."""
        docs = [
            RagDocument(
                id="1",
                content="Test message",
                channel_name="general",
                user_name="john",
                score=0.9,
            )
        ]
        result = build_context_string(docs)
        assert "Test message" in result
        assert "#general" in result

    def test_multiple_results(self):
        """Test with multiple results."""
        docs = [
            RagDocument(id=str(i), content=f"Message {i}", channel_name="general", score=0.9)
            for i in range(3)
        ]
        result = build_context_string(docs)
        assert "Relevant messages" in result
        assert "Message 0" in result
        assert "Message 1" in result


class TestParseQueryFilters:
    """Test query filter parsing."""

    def test_no_channel(self):
        """Test query without channel."""
        filters = parse_query_filters("what was discussed earlier")
        assert filters.get("channel_name") is None

    def test_with_channel(self):
        """Test query with channel."""
        filters = parse_query_filters("what was discussed in #general")
        assert filters.get("channel_name") == "general"

    def test_with_multiple_channels(self):
        """Test query with multiple channels (uses first)."""
        filters = parse_query_filters("check #general and #random")
        assert filters.get("channel_name") == "general"