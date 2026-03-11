"""Main entry point for vv-clawbot."""

import asyncio
import signal
import sys

from .channels import slack as slack_module
from .config import settings
from .database import close_database, initialize_database
from .logger import logger
from .mcp import get_connected_servers, initialize_mcp, is_mcp_enabled, shutdown_mcp
from .memory import initialize_memory, is_memory_enabled
from .rag import (
    get_document_count,
    initialize_vector_store,
)
from .rag import (
    start_indexer as start_rag_indexer,
)
from .rag import (
    stop_indexer as stop_rag_indexer,
)
from .tools.scheduler import start as start_scheduler
from .tools.scheduler import stop as stop_scheduler


async def main() -> None:
    """Main application entry point."""
    logger.info("=" * 50)
    logger.info("Starting vv-clawbot (Python)")
    logger.info("=" * 50)

    try:
        # 1. Initialize SQLite database
        logger.info("Initializing database...")
        await initialize_database()
        logger.info("Database initialized")

        # 2. Initialize RAG system
        if settings.rag.enabled:
            logger.info("Initializing RAG system...")
            await initialize_vector_store()
            doc_count = await get_document_count()
            logger.info(f"Vector store initialized ({doc_count} documents)")
            start_rag_indexer()
            logger.info("Background indexer started")
        else:
            logger.info("RAG system disabled")

        # 3. Initialize memory system
        if settings.memory.enabled:
            logger.info("Initializing memory system...")
            memory_ok = await initialize_memory()
            if memory_ok and is_memory_enabled():
                logger.info("Memory system initialized")
            else:
                logger.warning("Memory system failed to initialize")
        else:
            logger.info("Memory system disabled")

        # 4. Initialize MCP servers
        logger.info("Initializing MCP servers...")
        await initialize_mcp()
        if is_mcp_enabled():
            servers = get_connected_servers()
            logger.info(f"MCP initialized: {', '.join(servers)}")
        else:
            logger.info("No MCP servers connected")

        # 5. Start task scheduler
        if settings.features.task_scheduler:
            logger.info("Starting task scheduler...")
            start_scheduler()
            logger.info("Task scheduler started")

        # 6. Start Slack app
        logger.info("Starting Slack app...")
        await slack_module.start_slack_app()
        logger.info("Slack app started")

        # Ready!
        logger.info("=" * 50)
        logger.info("vv-clawbot is running!")
        logger.info("=" * 50)
        logger.info("Features enabled:")
        logger.info(f"  • RAG: {'yes' if settings.rag.enabled else 'no'}")
        logger.info(
            f"  • Memory: {'yes' if settings.memory.enabled and is_memory_enabled() else 'no'}"
        )
        logger.info(f"  • MCP: {'yes' if is_mcp_enabled() else 'no'}")
        logger.info(f"  • Scheduler: {'yes' if settings.features.task_scheduler else 'no'}")
        logger.info(f"  • Model: {settings.ai.default_model}")
        logger.info("=" * 50)
        logger.info("Press Ctrl+C to stop")

    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


async def shutdown(signal_name: str) -> None:
    """Graceful shutdown handler."""
    logger.info(f"\n{signal_name} received, shutting down...")

    try:
        # Stop Slack
        logger.info("Stopping Slack app...")
        await slack_module.stop_slack_app()

        # Stop MCP
        logger.info("Stopping MCP servers...")
        await shutdown_mcp()

        # Stop indexer
        if settings.rag.enabled:
            logger.info("Stopping indexer...")
            stop_rag_indexer()

        # Stop scheduler
        if settings.features.task_scheduler:
            logger.info("Stopping scheduler...")
            stop_scheduler()

        # Close database
        logger.info("Closing database...")
        await close_database()

        logger.info("Shutdown complete")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        sys.exit(1)


def _handle_signal(signum: int, _frame: object) -> None:
    """Handle shutdown signals by scheduling graceful shutdown."""
    sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
    try:
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(lambda: asyncio.ensure_future(shutdown(sig_name), loop=loop))
    except RuntimeError:
        # No running loop - process not fully started
        sys.exit(0)


def run() -> None:
    """Entry point for vv-clawbot."""
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    asyncio.run(main())


if __name__ == "__main__":
    run()
