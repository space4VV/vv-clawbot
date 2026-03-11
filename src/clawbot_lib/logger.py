"""Logging configuration using Python's built-in logging."""

import logging
import sys
from pathlib import Path

from .config import settings


def setup_logging() -> logging.Logger:
    """Configure logging for the application."""
    log_level = getattr(logging, settings.app.log_level.upper(), logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger for vv-clawbot
    error_handler = logging.FileHandler(log_dir / "error.log")
    error_handler.setLevel(logging.ERROR)
    combined_handler = logging.FileHandler(log_dir / "combined.log")
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            error_handler,
            combined_handler,
        ],
    )

    return logging.getLogger("vv-clawbot")


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: The name of the module (typically __name__).

    Returns:
        A configured logger instance.
    """
    return logging.getLogger(f"vv-clawbot.{name}")


# Initialize logging at module import
logger = setup_logging()
