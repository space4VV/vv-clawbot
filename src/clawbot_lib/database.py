"""Database management using aiosqlite."""

import json
from pathlib import Path
from typing import Any

import aiosqlite

from .config import settings
from .logger import get_logger
from .models import (
    Message,
    MessageRole,
    ScheduledTask,
    Session,
    SessionType,
    TaskStatus,
)

logger = get_logger("database")

_db_path: Path | None = None


def _get_db_path() -> Path:
    """Get database path and ensure directory exists."""
    global _db_path
    if _db_path is None:
        _db_path = Path(settings.app.database_path)
        _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


async def init_schema() -> None:
    """Initialize database schema."""
    logger.info("Initializing database schema...")

    async with aiosqlite.connect(_get_db_path()) as db:
        # Enable WAL mode
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        # Sessions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                channel_id TEXT,
                thread_ts TEXT,
                session_type TEXT NOT NULL DEFAULT 'dm',
                created_at INTEGER NOT NULL,
                last_activity INTEGER NOT NULL,
                metadata TEXT
            )
        """)

        # Messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                slack_ts TEXT,
                thread_ts TEXT,
                created_at INTEGER NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        # Scheduled tasks table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                thread_ts TEXT,
                task_description TEXT NOT NULL,
                cron_expression TEXT,
                scheduled_time INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                executed_at INTEGER,
                metadata TEXT
            )
        """)

        # Pairing codes
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pairing_codes (
                code TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Approved users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS approved_users (
                user_id TEXT PRIMARY KEY,
                approved_at INTEGER NOT NULL,
                approved_by TEXT
            )
        """)

        # Indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_channel ON sessions(channel_id)")
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status ON scheduled_tasks(status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_pairing_codes_user ON pairing_codes(user_id)"
        )

        await db.commit()

    logger.info("Database schema initialized")


async def initialize_database() -> None:
    """Initialize the database. Safe to call multiple times."""
    await init_schema()
    logger.info("Database ready")


def _row_to_session(row: tuple) -> Session:
    """Convert database row to Session model."""
    return Session(
        id=row[0],
        user_id=row[1],
        channel_id=row[2],
        thread_ts=row[3],
        session_type=SessionType(row[4]),
        created_at=row[5],
        last_activity=row[6],
        metadata=json.loads(row[7]) if row[7] else None,
    )


def _row_to_message(row: tuple) -> Message:
    """Convert database row to Message model."""
    return Message(
        id=row[0],
        session_id=row[1],
        role=MessageRole(row[2]),
        content=row[3],
        slack_ts=row[4],
        thread_ts=row[5],
        created_at=row[6],
        metadata=json.loads(row[7]) if row[7] else None,
    )


def _row_to_task(row: tuple) -> ScheduledTask:
    """Convert database row to ScheduledTask model."""
    return ScheduledTask(
        id=row[0],
        user_id=row[1],
        channel_id=row[2],
        thread_ts=row[3],
        task_description=row[4],
        cron_expression=row[5],
        scheduled_time=row[6],
        status=TaskStatus(row[7]),
        created_at=row[8],
        executed_at=row[9],
        metadata=json.loads(row[10]) if row[10] else None,
    )


# ============================================
# Session Management
# ============================================


async def get_or_create_session(
    user_id: str,
    channel_id: str | None,
    thread_ts: str | None,
) -> Session:
    """Get or create a session for the given context."""
    # Generate session ID based on context
    if thread_ts:
        session_id = f"thread:{channel_id}:{thread_ts}"
        session_type = SessionType.THREAD
    elif channel_id and not channel_id.startswith("D"):
        session_id = f"channel:{channel_id}"
        session_type = SessionType.CHANNEL
    else:
        session_id = f"dm:{user_id}"
        session_type = SessionType.DM

    import time

    now = int(time.time())

    async with aiosqlite.connect(_get_db_path()) as db:
        # Check if session exists
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()

        if row:
            # Update last activity
            await db.execute(
                "UPDATE sessions SET last_activity = ? WHERE id = ?",
                (now, session_id),
            )
            await db.commit()
            return _row_to_session(row)

        # Create new session
        await db.execute(
            """INSERT INTO sessions (id, user_id, channel_id, thread_ts, session_type, created_at, last_activity)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, channel_id, thread_ts, session_type.value, now, now),
        )
        await db.commit()

    return Session(
        id=session_id,
        user_id=user_id,
        channel_id=channel_id,
        thread_ts=thread_ts,
        session_type=session_type,
        created_at=now,
        last_activity=now,
        metadata=None,
    )


async def get_session(session_id: str) -> Session | None:
    """Get a session by ID."""
    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()

    if not row:
        return None

    return _row_to_session(row)


# ============================================
# Message History
# ============================================


async def add_message(
    session_id: str,
    role: MessageRole,
    content: str,
    slack_ts: str | None = None,
    thread_ts: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Message:
    """Add a message to the session history."""
    import time

    now = int(time.time())

    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            """INSERT INTO messages (session_id, role, content, slack_ts, thread_ts, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                role.value,
                content,
                slack_ts,
                thread_ts,
                json.dumps(metadata) if metadata else None,
                now,
            ),
        )
        await db.commit()
        row_id = cursor.lastrowid

    return Message(
        id=row_id,
        session_id=session_id,
        role=role,
        content=content,
        slack_ts=slack_ts,
        thread_ts=thread_ts,
        created_at=now,
        metadata=metadata,
    )


async def get_session_history(
    session_id: str,
    limit: int | None = None,
) -> list[Message]:
    """Get message history for a session."""
    limit = limit or settings.app.max_history_messages

    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            """SELECT * FROM messages
               WHERE session_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (session_id, limit),
        )
        rows = await cursor.fetchall()

    messages = [_row_to_message(row) for row in rows]
    return list(reversed(messages))


async def get_thread_messages(channel_id: str, thread_ts: str) -> list[Message]:
    """Get all messages in a thread."""
    session_id = f"thread:{channel_id}:{thread_ts}"
    return await get_session_history(session_id, limit=100)


async def clear_session_history(session_id: str) -> None:
    """Clear message history for a session."""
    async with aiosqlite.connect(_get_db_path()) as db:
        await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await db.commit()
    logger.info(f"Cleared history for session: {session_id}")


# ============================================
# Scheduled Tasks
# ============================================


async def create_scheduled_task(
    user_id: str,
    channel_id: str,
    task_description: str,
    scheduled_time: int | None = None,
    cron_expression: str | None = None,
    thread_ts: str | None = None,
) -> ScheduledTask:
    """Create a new scheduled task."""
    import time

    now = int(time.time())

    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            """INSERT INTO scheduled_tasks
               (user_id, channel_id, thread_ts, task_description, cron_expression, scheduled_time, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                channel_id,
                thread_ts,
                task_description,
                cron_expression,
                scheduled_time,
                now,
            ),
        )
        await db.commit()
        row_id = cursor.lastrowid

    return ScheduledTask(
        id=row_id,
        user_id=user_id,
        channel_id=channel_id,
        thread_ts=thread_ts,
        task_description=task_description,
        cron_expression=cron_expression,
        scheduled_time=scheduled_time,
        status=TaskStatus.PENDING,
        created_at=now,
        executed_at=None,
        metadata=None,
    )


async def get_pending_tasks() -> list[ScheduledTask]:
    """Get all pending tasks."""
    import time

    now = int(time.time())

    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            """SELECT * FROM scheduled_tasks
               WHERE status = 'pending'
               AND (scheduled_time IS NULL OR scheduled_time <= ?)
               ORDER BY scheduled_time ASC""",
            (now,),
        )
        rows = await cursor.fetchall()

    return [_row_to_task(row) for row in rows]


async def update_task_status(task_id: int, status: TaskStatus) -> None:
    """Update task status."""
    import time

    now = int(time.time())

    async with aiosqlite.connect(_get_db_path()) as db:
        await db.execute(
            """UPDATE scheduled_tasks
               SET status = ?,
                   executed_at = CASE WHEN ? IN ('completed', 'failed') THEN ? ELSE executed_at END
               WHERE id = ?""",
            (status.value, status.value, now, task_id),
        )
        await db.commit()


async def get_user_tasks(user_id: str) -> list[ScheduledTask]:
    """Get tasks for a user."""
    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            """SELECT * FROM scheduled_tasks
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT 20""",
            (user_id,),
        )
        rows = await cursor.fetchall()

    return [_row_to_task(row) for row in rows]


async def cancel_task(task_id: int, user_id: str) -> bool:
    """Cancel a pending task."""
    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            """UPDATE scheduled_tasks
               SET status = 'cancelled'
               WHERE id = ? AND user_id = ? AND status = 'pending'""",
            (task_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


# ============================================
# DM Pairing Security
# ============================================


async def generate_pairing_code(user_id: str) -> str:
    """Generate a pairing code for DM access."""
    import random
    import string
    import time

    # Generate 6-character alphanumeric code
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    expires_at = int(time.time()) + 3600  # 1 hour
    now = int(time.time())

    async with aiosqlite.connect(_get_db_path()) as db:
        # Delete any existing codes for this user
        await db.execute("DELETE FROM pairing_codes WHERE user_id = ?", (user_id,))

        # Create new code
        await db.execute(
            """INSERT INTO pairing_codes (code, user_id, expires_at, created_at)
               VALUES (?, ?, ?, ?)""",
            (code, user_id, expires_at, now),
        )
        await db.commit()

    return code


async def verify_pairing_code(code: str) -> str | None:
    """Verify a pairing code and return the user ID if valid."""
    import time

    now = int(time.time())

    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            """SELECT user_id FROM pairing_codes
               WHERE code = ? AND expires_at > ? AND approved = 0""",
            (code.upper(), now),
        )
        row = await cursor.fetchone()

    return row[0] if row else None


async def approve_pairing(code: str, approved_by: str) -> bool:
    """Approve a pairing code."""
    user_id = await verify_pairing_code(code)
    if not user_id:
        return False

    import time

    now = int(time.time())

    async with aiosqlite.connect(_get_db_path()) as db:
        await db.execute(
            "UPDATE pairing_codes SET approved = 1 WHERE code = ?",
            (code.upper(),),
        )
        await db.execute(
            """INSERT OR REPLACE INTO approved_users (user_id, approved_at, approved_by)
               VALUES (?, ?, ?)""",
            (user_id, now, approved_by),
        )
        await db.commit()

    return True


async def is_user_approved(user_id: str) -> bool:
    """Check if a user is approved for DM access."""
    # Check if user is in allowed list
    if "*" in settings.security.parse_allowed_users:
        return True
    if user_id in settings.security.parse_allowed_users:
        return True

    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            "SELECT 1 FROM approved_users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()

    return row is not None


# ============================================
# Cleanup and Maintenance
# ============================================


async def cleanup_old_sessions(max_age_seconds: int = 86400 * 7) -> int:
    """Clean up old sessions."""
    import time

    cutoff = int(time.time()) - max_age_seconds

    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            "DELETE FROM sessions WHERE last_activity < ?",
            (cutoff,),
        )
        await db.commit()
        count = cursor.rowcount

    logger.info(f"Cleaned up {count} old sessions")
    return count


async def cleanup_expired_pairing_codes() -> int:
    """Clean up expired pairing codes."""
    import time

    now = int(time.time())

    async with aiosqlite.connect(_get_db_path()) as db:
        cursor = await db.execute(
            "DELETE FROM pairing_codes WHERE expires_at < ? AND approved = 0",
            (now,),
        )
        await db.commit()
        count = cursor.rowcount

    return count


async def close_database() -> None:
    """Close database connections."""
    logger.info("Database closed")
