"""Memory module using mem0."""

from __future__ import annotations

import os

from mem0 import Memory

from ..config import settings
from ..logger import get_logger
from ..models import MemoryItem

logger = get_logger("memory")


class MemoryClient:
    """Memory client using the modern mem0 `Memory` API."""

    def __init__(self) -> None:
        self._client: Memory | None = None

    @property
    def client(self) -> Memory | None:
        """Get the mem0 client, if configured.

        We initialise mem0 in a way that works even if the OpenAI API key is
        provided either via:

        - `OPENAI_API_KEY` in the environment, or
        - `AI_OPENAI_API_KEY` / Settings, as used elsewhere in this project.
        """
        if self._client is None:
            # Prefer explicit env var, but fall back to nested settings field and
            # the AI_* names we use in .env. When we find a key, we ensure
            # OPENAI_API_KEY is set so mem0's internals can see it.
            openai_key = (
                os.environ.get("OPENAI_API_KEY")
                or os.environ.get("AI_OPENAI_API_KEY")
                or (settings.ai.openai_api_key or None)
            )

            if openai_key:
                os.environ.setdefault("OPENAI_API_KEY", openai_key)
                try:
                    self._client = Memory()
                    logger.info("mem0 Memory client created")
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error("Failed to initialize mem0 Memory client: %s", exc)
                    self._client = None
            elif settings.ai.anthropic_api_key:
                logger.warning(
                    "mem0 currently requires an OpenAI-compatible API key; "
                    "Anthropic-only configuration will run without long-term memory.",
                )
                self._client = None
            else:
                logger.warning("No API key configured for memory; disabling mem0 integration")
                self._client = None
        return self._client

    async def initialize(self) -> bool:
        """Initialize the memory client."""
        if not settings.memory.enabled:
            logger.info("Memory disabled")
            return False

        if self.client is None:
            logger.warning("Memory client not initialized - no API key")
            return False

        logger.info("Memory system initialized")
        return True

    async def add(
        self,
        messages: list[dict[str, str]],
        user_id: str,
    ) -> None:
        """Add memories from conversation messages."""
        if not self.client:
            return

        try:
            # Convert messages to mem0 format
            for msg in messages:
                self.client.add(
                    message=msg.get("content", ""),
                    role=msg.get("role", "user"),
                    user_id=user_id,
                )
            logger.debug(f"Added {len(messages)} messages to memory for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> list[MemoryItem]:
        """Search memories for a user."""
        if not self.client:
            return []

        try:
            results = self.client.get_all(user_id=user_id)
            memories = []

            # Simple text search (mem0 has more advanced filtering)
            query_lower = query.lower()
            for item in results.get("results", []):
                memory_text = item.get("memory", "")
                if query_lower in memory_text.lower():
                    memories.append(
                        MemoryItem(
                            id=item.get("id"),
                            memory=memory_text,
                            score=1.0,
                        )
                    )

            return memories[:limit]
        except Exception as e:
            logger.error(f"Failed to search memory: {e}")
            return []

    async def get_all(self, user_id: str) -> list[MemoryItem]:
        """Get all memories for a user."""
        if not self.client:
            return []

        try:
            results = self.client.get_all(user_id=user_id)
            return [
                MemoryItem(
                    id=item.get("id"),
                    memory=item.get("memory", ""),
                    score=1.0,
                )
                for item in results.get("results", [])
            ]
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []

    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        if not self.client:
            return False

        try:
            self.client.delete(memory_id=memory_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False

    async def delete_all(self, user_id: str) -> bool:
        """Delete all memories for a user."""
        if not self.client:
            return False

        try:
            self.client.delete_all(user_id=user_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete all memories: {e}")
            return False


def build_memory_context(memories: list[MemoryItem]) -> str:
    """Build context string from memories."""
    if not memories:
        return ""

    lines = ["Previous conversation context about you:"]
    for i, mem in enumerate(memories, 1):
        lines.append(f"{i}. {mem.memory}")

    return "\n".join(lines)


# Global client
_memory_client: MemoryClient | None = None
_memory_enabled = False


async def initialize_memory() -> bool:
    """Initialize the memory system."""
    global _memory_client, _memory_enabled

    if not settings.memory.enabled:
        _memory_enabled = False
        return False

    _memory_client = MemoryClient()
    _memory_enabled = await _memory_client.initialize()
    return _memory_enabled


def is_memory_enabled() -> bool:
    """Check if memory is enabled."""
    return _memory_enabled


async def add_memory(
    messages: list[dict[str, str]],
    user_id: str,
) -> None:
    """Add memories from conversation."""
    if _memory_client and _memory_enabled:
        await _memory_client.add(messages, user_id)


async def search_memory(
    query: str,
    user_id: str,
    limit: int = 5,
) -> list[MemoryItem]:
    """Search memories."""
    if _memory_client and _memory_enabled:
        return await _memory_client.search(query, user_id, limit)
    return []


async def get_all_memories(user_id: str) -> list[MemoryItem]:
    """Get all memories for a user."""
    if _memory_client and _memory_enabled:
        return await _memory_client.get_all(user_id)
    return []


async def delete_memory(memory_id: str) -> bool:
    """Delete a memory."""
    if _memory_client and _memory_enabled:
        return await _memory_client.delete(memory_id)
    return False


async def delete_all_memories(user_id: str) -> bool:
    """Delete all memories for a user."""
    if _memory_client and _memory_enabled:
        return await _memory_client.delete_all(user_id)
    return False


# Aliases
initializeMemory = initialize_memory
isMemoryEnabled = is_memory_enabled
addMemory = add_memory
searchMemory = search_memory
getAllMemories = get_all_memories
deleteMemory = delete_memory
deleteAllMemories = delete_all_memories
buildMemoryContext = build_memory_context
