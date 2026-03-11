"""Tests for data models."""

import pytest
from pydantic import ValidationError

from clawbot_lib.models import (
    Session,
    SessionType,
    Message,
    MessageRole,
    ScheduledTask,
    TaskStatus,
    SlackUser,
    SlackChannel,
    RagDocument,
    AgentContext,
    AgentResponse,
    MemoryItem,
    MCPTool,
    MCPToolResult,
)


class TestSession:
    """Test Session model."""

    def test_create_session(self):
        """Test creating a session."""
        session = Session(
            id="dm:U12345",
            user_id="U12345",
            session_type=SessionType.DM,
        )
        assert session.id == "dm:U12345"
        assert session.user_id == "U12345"
        assert session.session_type == SessionType.DM

    def test_session_with_channel(self):
        """Test session with channel."""
        session = Session(
            id="channel:C12345",
            user_id="U12345",
            channel_id="C12345",
            session_type=SessionType.CHANNEL,
        )
        assert session.channel_id == "C12345"

    def test_session_with_thread(self):
        """Test session with thread."""
        session = Session(
            id="thread:C12345.123456",
            user_id="U12345",
            channel_id="C12345",
            thread_ts="123456.789",
            session_type=SessionType.THREAD,
        )
        assert session.thread_ts == "123456.789"


class TestMessage:
    """Test Message model."""

    def test_create_message(self):
        """Test creating a message."""
        message = Message(
            session_id="dm:U12345",
            role=MessageRole.USER,
            content="Hello, world!",
        )
        assert message.session_id == "dm:U12345"
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"

    def test_message_with_metadata(self):
        """Test message with metadata."""
        message = Message(
            session_id="dm:U12345",
            role=MessageRole.ASSISTANT,
            content="Hi there!",
            metadata={"intent": "greeting"},
        )
        assert message.metadata == {"intent": "greeting"}


class TestScheduledTask:
    """Test ScheduledTask model."""

    def test_create_task(self):
        """Test creating a task."""
        task = ScheduledTask(
            user_id="U12345",
            channel_id="C12345",
            task_description="Reminder message",
            scheduled_time=1234567890,
        )
        assert task.user_id == "U12345"
        assert task.status == TaskStatus.PENDING

    def test_task_status_transitions(self):
        """Test task status transitions."""
        task = ScheduledTask(
            user_id="U12345",
            channel_id="C12345",
            task_description="Test task",
            status=TaskStatus.RUNNING,
        )
        assert task.status == TaskStatus.RUNNING


class TestSlackUser:
    """Test SlackUser model."""

    def test_create_user(self):
        """Test creating a user."""
        user = SlackUser(
            id="U12345",
            name="johndoe",
            real_name="John Doe",
        )
        assert user.id == "U12345"
        assert user.real_name == "John Doe"


class TestSlackChannel:
    """Test SlackChannel model."""

    def test_create_channel(self):
        """Test creating a channel."""
        channel = SlackChannel(
            id="C12345",
            name="general",
            is_member=True,
        )
        assert channel.name == "general"
        assert channel.is_member is True


class TestRagDocument:
    """Test RagDocument model."""

    def test_create_document(self):
        """Test creating a RAG document."""
        doc = RagDocument(
            id="doc1",
            content="Test content",
            channel_name="general",
            user_name="johndoe",
            score=0.95,
        )
        assert doc.content == "Test content"
        assert doc.formatted == "[#general by johndoe] Test content"

    def test_formatted_without_channel(self):
        """Test formatted string without channel."""
        doc = RagDocument(id="doc1", content="Test")
        assert doc.formatted == "[unknown] Test"


class TestAgentContext:
    """Test AgentContext model."""

    def test_create_context(self):
        """Test creating agent context."""
        context = AgentContext(
            session_id="dm:U12345",
            user_id="U12345",
            channel_id="D12345",
            thread_ts=None,
        )
        assert context.session_id == "dm:U12345"


class TestAgentResponse:
    """Test AgentResponse model."""

    def test_create_response(self):
        """Test creating agent response."""
        response = AgentResponse(
            content="Hello!",
            should_thread=False,
            rag_used=False,
            sources_count=0,
            memory_used=False,
            memories_count=0,
        )
        assert response.content == "Hello!"
        assert response.should_thread is False


class TestMemoryItem:
    """Test MemoryItem model."""

    def test_create_memory_item(self):
        """Test creating a memory item."""
        item = MemoryItem(
            id="mem1",
            memory="User prefers dark mode",
            score=0.9,
        )
        assert item.memory == "User prefers dark mode"


class TestMCPTool:
    """Test MCPTool model."""

    def test_create_tool(self):
        """Test creating an MCP tool."""
        tool = MCPTool(
            name="github_search_repositories",
            description="Search GitHub repositories",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            server_name="github",
        )
        assert tool.name == "github_search_repositories"
        assert tool.server_name == "github"


class TestMCPToolResult:
    """Test MCPToolResult model."""

    def test_successful_result(self):
        """Test successful result."""
        result = MCPToolResult(success=True, result={"status": "ok"})
        assert result.success is True
        assert result.result == {"status": "ok"}

    def test_failed_result(self):
        """Test failed result."""
        result = MCPToolResult(success=False, error="Connection failed")
        assert result.success is False
        assert result.error == "Connection failed"