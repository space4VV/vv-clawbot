"""Data models using Pydantic v2."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class SessionType(StrEnum):
    """Type of conversation session."""

    DM = "dm"
    CHANNEL = "channel"
    THREAD = "thread"


class MessageRole(StrEnum):
    """Role of a message in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TaskStatus(StrEnum):
    """Status of a scheduled task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Session(BaseModel):
    """Conversation session model."""

    id: str
    user_id: str
    channel_id: str | None = None
    thread_ts: str | None = None
    session_type: SessionType = SessionType.DM
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    last_activity: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    metadata: dict[str, Any] | None = None

    model_config = {"use_enum_values": True}


class Message(BaseModel):
    """Message model."""

    id: int | None = None
    session_id: str
    role: MessageRole
    content: str
    slack_ts: str | None = None
    thread_ts: str | None = None
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    metadata: dict[str, Any] | None = None

    model_config = {"use_enum_values": True}


class ScheduledTask(BaseModel):
    """Scheduled task model."""

    id: int | None = None
    user_id: str
    channel_id: str
    thread_ts: str | None = None
    task_description: str
    cron_expression: str | None = None
    scheduled_time: int | None = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    executed_at: int | None = None
    metadata: dict[str, Any] | None = None

    model_config = {"use_enum_values": True}


class PairingCode(BaseModel):
    """Pairing code for DM security."""

    code: str
    user_id: str
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    expires_at: int
    approved: bool = False


class ApprovedUser(BaseModel):
    """Approved user for DM access."""

    user_id: str
    approved_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    approved_by: str | None = None


class SlackUser(BaseModel):
    """Slack user model."""

    id: str
    name: str
    real_name: str | None = None
    is_bot: bool = False


class SlackChannel(BaseModel):
    """Slack channel model."""

    id: str
    name: str
    is_member: bool = False


class SlackMessage(BaseModel):
    """Slack message model."""

    ts: str
    channel: str
    user: str | None = None
    text: str
    thread_ts: str | None = None
    subtype: str | None = None


class RagDocument(BaseModel):
    """RAG document model."""

    id: str
    content: str
    channel_name: str | None = None
    user_name: str | None = None
    ts: str | None = None
    score: float = 0.0

    @computed_field
    def formatted(self) -> str:
        """Format document for display."""
        source = f"#{self.channel_name}" if self.channel_name else "unknown"
        if self.user_name:
            source += f" by {self.user_name}"
        return f"[{source}] {self.content}"


class AgentContext(BaseModel):
    """Agent execution context."""

    session_id: str
    user_id: str
    channel_id: str | None = None
    thread_ts: str | None = None
    channel_name: str | None = None
    user_name: str | None = None


class AgentResponse(BaseModel):
    """Agent response model."""

    content: str
    should_thread: bool = False
    rag_used: bool = False
    sources_count: int = 0
    memory_used: bool = False
    memories_count: int = 0


class MemoryItem(BaseModel):
    """Memory item from mem0."""

    id: str | None = None
    memory: str
    score: float = 0.0


class MCPTool(BaseModel):
    """MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str


class MCPToolResult(BaseModel):
    """Result from MCP tool execution."""

    success: bool
    result: Any = None
    error: str | None = None


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""

    name: str
    command: str
    args: list[str]
    env: dict[str, str]


class RetrieveResult(BaseModel):
    """Result from RAG retrieval."""

    results: list[RagDocument]
