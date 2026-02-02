"""
Logging Configuration
=====================
Centralized logging with file rotation and structured output.
"""

import sys
from pathlib import Path
from loguru import logger

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Remove default handler
logger.remove()

# Console handler (INFO and above)
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    colorize=True,
)

# File handler (DEBUG and above, with rotation)
logger.add(
    LOGS_DIR / "app_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="1 day",
    retention="7 days",
    compression="zip",
)

# Error-specific file (for quick debugging)
logger.add(
    LOGS_DIR / "errors.log",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
    rotation="1 week",
    retention="1 month",
)

__all__ = ["logger"]
