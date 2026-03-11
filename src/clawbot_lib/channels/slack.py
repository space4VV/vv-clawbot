"""Slack client and bot integration.

This module provides two layers:

1. A thin wrapper around the Slack Web API (`SlackClient`).
2. A Socket Mode integration that listens for message events and routes them
   into the Python agent.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from threading import Thread
from typing import Any, Callable

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from ..config import settings
from ..logger import get_logger
from ..models import AgentContext, SlackChannel, SlackMessage, SlackUser

logger = get_logger("slack")


class SlackClient:
    """Slack Web API client."""

    def __init__(self) -> None:
        # Ensure .env values are available in os.environ for Slack SDK and mem0.
        load_dotenv()

        # Prefer explicit env var if set; fall back to nested settings.
        token = os.environ.get("SLACK_BOT_TOKEN") or settings.slack.bot_token
        if not token:
            logger.error("SLACK_BOT_TOKEN is not configured; Slack client will not authenticate")

        self._client = WebClient(token=token)

        user_token = os.environ.get("SLACK_USER_TOKEN") or settings.slack.user_token
        self._user_client = WebClient(token=user_token) if user_token else None

    @property
    def client(self) -> WebClient:
        """Get the Slack client."""
        return self._client

    async def send_message(
        self,
        target: str,
        message: str,
        thread_ts: str | None = None,
    ) -> tuple[bool, str | None]:
        """Send a message to a channel or user.

        Args:
            target: Channel name (e.g., "general") or user ID
            message: Message to send
            thread_ts: Thread timestamp to reply to

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Resolve target to channel ID if it's a channel name
            channel_id = target
            if not target.startswith("C") and not target.startswith("D"):
                channel = await self.find_channel(target)
                if channel:
                    channel_id = channel.id
                else:
                    return False, f"Channel not found: {target}"

            self._client.chat_postMessage(
                channel=channel_id,
                text=message,
                thread_ts=thread_ts,
            )
            return True, None
        except SlackApiError as e:
            logger.error(f"Failed to send message: {e}")
            return False, str(e)

    async def get_conversation_history(
        self,
        channel_id: str,
        limit: int = 20,
    ) -> list[SlackMessage]:
        """Get conversation history for a channel."""
        try:
            response = self._client.conversations_history(
                channel=channel_id,
                limit=limit,
            )
            messages = []
            for msg in response["messages"]:
                messages.append(
                    SlackMessage(
                        ts=msg["ts"],
                        channel=channel_id,
                        user=msg.get("user"),
                        text=msg.get("text", ""),
                        thread_ts=msg.get("thread_ts"),
                        subtype=msg.get("subtype"),
                    )
                )
            return messages
        except SlackApiError as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    async def find_user(self, user_id: str) -> SlackUser | None:
        """Find a user by ID."""
        try:
            response = self._client.users_info(user=user_id)
            user_info = response["user"]
            return SlackUser(
                id=user_info["id"],
                name=user_info["name"],
                real_name=user_info.get("real_name"),
                is_bot=user_info.get("is_bot", False),
            )
        except SlackApiError:
            return None

    async def find_user_by_name(self, name: str) -> SlackUser | None:
        """Find a user by name."""
        try:
            response = self._client.users_lookup_by_name(name=name)
            user_info = response["user"]
            return SlackUser(
                id=user_info["id"],
                name=user_info["name"],
                real_name=user_info.get("real_name"),
                is_bot=user_info.get("is_bot", False),
            )
        except SlackApiError:
            return None

    async def find_channel(self, channel_name: str) -> SlackChannel | None:
        """Find a channel by name."""
        try:
            # Remove # prefix if present
            channel_name = channel_name.lstrip("#")

            response = self._client.conversations_list()
            for channel in response["channels"]:
                if channel["name"] == channel_name:
                    return SlackChannel(
                        id=channel["id"],
                        name=channel["name"],
                        is_member=channel.get("is_member", False),
                    )
            return None
        except SlackApiError:
            return None

    async def list_channels(self) -> list[SlackChannel]:
        """List all accessible channels."""
        try:
            response = self._client.conversations_list()
            channels = []
            for channel in response["channels"]:
                channels.append(
                    SlackChannel(
                        id=channel["id"],
                        name=channel["name"],
                        is_member=channel.get("is_member", False),
                    )
                )
            return channels
        except SlackApiError as e:
            logger.error(f"Failed to list channels: {e}")
            return []

    async def list_users(self) -> list[SlackUser]:
        """List all users in the workspace."""
        try:
            response = self._client.users_list()
            users = []
            for user in response["members"]:
                if user.get("is_bot") or user.get("deleted"):
                    continue
                users.append(
                    SlackUser(
                        id=user["id"],
                        name=user["name"],
                        real_name=user.get("real_name"),
                        is_bot=user.get("is_bot", False),
                    )
                )
            return users
        except SlackApiError as e:
            logger.error(f"Failed to list users: {e}")
            return []

    async def schedule_message(
        self,
        target: str,
        message: str,
        post_at: int,
    ) -> tuple[bool, str | None]:
        """Schedule a message to be sent later.

        Args:
            target: Channel name or ID
            message: Message to send
            post_at: Unix timestamp when to post

        Returns:
            Tuple of (success, error_message)
        """
        try:
            channel_id = target
            if not target.startswith("C"):
                channel = await self.find_channel(target)
                if channel:
                    channel_id = channel.id
                else:
                    return False, f"Channel not found: {target}"

            self._client.chat_scheduleMessage(
                channel=channel_id,
                text=message,
                post_at=post_at,
            )
            return True, None
        except SlackApiError as e:
            logger.error(f"Failed to schedule message: {e}")
            return False, str(e)

    async def list_scheduled_messages(self, channel_id: str) -> list[dict[str, Any]]:
        """List scheduled messages for a channel."""
        try:
            response = self._client.chat_scheduledMessages_list(
                channel=channel_id,
            )
            return response.get("scheduled_messages", [])
        except SlackApiError as e:
            logger.error(f"Failed to list scheduled messages: {e}")
            return []

    async def delete_scheduled_message(self, scheduled_message_id: str) -> bool:
        """Delete a scheduled message."""
        try:
            self._client.chat_deleteScheduledMessage(
                scheduled_message_id=scheduled_message_id,
            )
            return True
        except SlackApiError as e:
            logger.error(f"Failed to delete scheduled message: {e}")
            return False

    async def set_reminder(
        self,
        user_id: str,
        text: str,
        time: str,
    ) -> tuple[bool, str | None]:
        """Set a reminder for a user."""
        try:
            # Parse time - this is a simplified version
            # In production, you'd want to parse natural language times

            # Calculate Unix timestamp from relative time
            # For now, assume time is a Unix timestamp or ISO format
            try:
                ts = int(time)
            except ValueError:
                return False, "Invalid time format"

            if self._user_client:
                self._user_client.reminders_add(
                    text=text,
                    time=ts,
                    user=user_id,
                )
                return True, None
            else:
                return False, "User token not configured"
        except SlackApiError as e:
            logger.error(f"Failed to set reminder: {e}")
            return False, str(e)

    async def list_reminders(self, user_id: str) -> list[dict[str, Any]]:
        """List reminders for a user."""
        try:
            if self._user_client:
                response = self._user_client.reminders_list(user=user_id)
                return response.get("reminders", [])
            return []
        except SlackApiError as e:
            logger.error(f"Failed to list reminders: {e}")
            return []

    async def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder."""
        try:
            if self._user_client:
                self._user_client.reminders_delete(id=reminder_id)
                return True
            return False
        except SlackApiError:
            return False


def format_messages_for_context(messages: list[SlackMessage]) -> str:
    """Format Slack messages for LLM context."""
    lines = []
    for msg in messages:
        user = msg.user or "unknown"
        lines.append(f"[{user}]: {msg.text}")
    return "\n".join(lines)


# Global client and Socket Mode instances
_slack_client: SlackClient | None = None
_socket_client: SocketModeClient | None = None


def get_slack_client() -> SlackClient:
    """Get the global Slack client instance."""
    global _slack_client
    if _slack_client is None:
        _slack_client = SlackClient()
    return _slack_client


async def start_slack_app() -> None:
    """Start the Slack app and attach a Socket Mode listener.

    This function:
    - Verifies the Web API token via auth.test.
    - Starts a Socket Mode client in a background thread.
    - Routes incoming message events to the Python agent.
    """

    logger.info("Starting Slack app...")
    slack_client = get_slack_client()

    # First, verify the bot token is valid.
    try:
        slack_client.client.auth_test()
    except SlackApiError as e:
        logger.error(f"Failed to start Slack app: {e}")
        raise

    app_token = os.environ.get("SLACK_APP_TOKEN") or settings.slack.app_token
    if not app_token:
        logger.error("SLACK_APP_TOKEN is not configured; Socket Mode will not start")
        raise RuntimeError("SLACK_APP_TOKEN is required for Socket Mode")

    loop = asyncio.get_running_loop()

    def handle_socket_mode_request(client: SocketModeClient, req: SocketModeRequest) -> None:
        """Handle incoming Socket Mode requests from Slack."""
        if req.type != "events_api":
            return

        # Acknowledge the event so Slack doesn't retry.
        client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

        event = req.payload.get("event", {})
        if not event:
            return

        if event.get("type") != "message":
            return

        # Ignore messages from bots (including ourselves).
        if event.get("bot_id"):
            return

        user_id = event.get("user")
        channel_id = event.get("channel")
        text = event.get("text", "") or ""
        thread_ts = event.get("thread_ts")
        ts = event.get("ts")

        if not user_id or not channel_id or not text:
            return

        # Build an AgentContext using the same session semantics as the DB layer.
        if thread_ts:
            session_id = f"thread:{channel_id}:{thread_ts}"
        elif channel_id.startswith("C"):
            session_id = f"channel:{channel_id}"
        else:
            session_id = f"dm:{user_id}"

        context = AgentContext(
            session_id=session_id,
            user_id=user_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            channel_name=None,
            user_name=None,
        )

        async def run_agent() -> None:
            from ..agent import process_message  # Imported lazily to avoid circular import

            try:
                response = await process_message(text, context)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Agent processing failed: %s", exc, exc_info=True)
                return

            reply_thread_ts = thread_ts or ts
            await slack_client.send_message(channel_id, response.content, reply_thread_ts)

        # Schedule the coroutine on the main event loop from the Socket Mode thread.
        asyncio.run_coroutine_threadsafe(run_agent(), loop)

    # Create and start Socket Mode client in a background thread.
    global _socket_client
    _socket_client = SocketModeClient(
        app_token=app_token,
        web_client=slack_client.client,
    )
    _socket_client.socket_mode_request_listeners.append(handle_socket_mode_request)

    def run_socket_client() -> None:
        try:
            _socket_client.connect()
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Socket Mode client stopped: %s", exc, exc_info=True)

    thread = Thread(target=run_socket_client, name="slack-socket-mode", daemon=True)
    thread.start()

    logger.info("Slack app started")


async def stop_slack_app() -> None:
    """Stop the Slack app."""
    logger.info("Stopping Slack app...")
    global _slack_client
    _slack_client = None
    logger.info("Slack app stopped")


# Aliases for backward compatibility
async def send_message(
    target: str, message: str, thread_ts: str | None = None
) -> tuple[bool, str | None]:
    """Send a message (alias for get_slack_client().send_message)."""
    return await get_slack_client().send_message(target, message, thread_ts)


async def get_channel_history(
    channel_id: str, limit: int = 20
) -> list[SlackMessage]:
    """Get channel history (alias)."""
    return await get_slack_client().get_conversation_history(channel_id, limit)


async def find_user(user_id: str) -> SlackUser | None:
    """Find user (alias)."""
    return await get_slack_client().find_user(user_id)


async def find_channel(channel_name: str) -> SlackChannel | None:
    """Find channel (alias)."""
    return await get_slack_client().find_channel(channel_name)


async def list_users() -> list[SlackUser]:
    """List users (alias)."""
    return await get_slack_client().list_users()


async def list_channels() -> list[SlackChannel]:
    """List channels (alias)."""
    return await get_slack_client().list_channels()


async def schedule_message(
    target: str, message: str, send_at: datetime | int
) -> tuple[bool, str | None]:
    """Schedule message (alias)."""
    ts = int(send_at.timestamp()) if isinstance(send_at, datetime) else int(send_at)
    return await get_slack_client().schedule_message(target, message, ts)


async def list_scheduled_messages(channel_id: str) -> list[dict[str, Any]]:
    """List scheduled messages (alias)."""
    return await get_slack_client().list_scheduled_messages(channel_id)


async def delete_scheduled_message(msg_id: str) -> bool:
    """Delete scheduled message (alias)."""
    return await get_slack_client().delete_scheduled_message(msg_id)


async def set_reminder(
    user_id: str, text: str, time: str | int
) -> tuple[bool, str | None]:
    """Set reminder (alias)."""
    return await get_slack_client().set_reminder(user_id, text, time)


async def list_reminders(user_id: str) -> list[dict[str, Any]]:
    """List reminders (alias)."""
    return await get_slack_client().list_reminders(user_id)


async def delete_reminder(reminder_id: str) -> bool:
    """Delete reminder (alias)."""
    return await get_slack_client().delete_reminder(reminder_id)
