"""PostgresSaver checkpointer module with singleton pattern.

This module provides a singleton instance of PostgresSaver for maintaining
conversation state across graph executions. The checkpointer:
- Stores conversation history and state snapshots
- Enables resume/replay functionality
- Maintains thread-based conversation isolation

Usage:
    from src.shared.checkpointer import get_checkpointer

    checkpointer = await get_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)
"""

import logging
import os
from typing import Optional

from langgraph.checkpoint.postgres import PostgresSaver

logger = logging.getLogger(__name__)

# Singleton instance
_checkpointer_instance: Optional[PostgresSaver] = None


async def get_checkpointer() -> PostgresSaver:
    """
    Get or create a singleton PostgresSaver checkpointer instance.

    This function implements the singleton pattern to ensure only one
    checkpointer instance exists throughout the application lifecycle.

    The checkpointer automatically creates required database tables on
    first initialization via PostgresSaver.setup().

    Returns:
        PostgresSaver: The singleton checkpointer instance.

    Raises:
        ValueError: If DATABASE_URL environment variable is not set.

    Example:
        >>> checkpointer = await get_checkpointer()
        >>> graph = builder.compile(checkpointer=checkpointer)
    """
    global _checkpointer_instance

    # Return existing instance if already created
    if _checkpointer_instance is not None:
        return _checkpointer_instance

    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please set it to your PostgreSQL connection string."
        )

    logger.info("Initializing PostgresSaver checkpointer from DATABASE_URL")

    try:
        # Create PostgresSaver instance from connection string
        checkpointer = PostgresSaver.from_conn_string(database_url)

        # Setup database tables (idempotent operation)
        await checkpointer.setup()

        # Store as singleton
        _checkpointer_instance = checkpointer

        logger.info("PostgresSaver checkpointer initialized successfully")
        return _checkpointer_instance

    except Exception as e:
        logger.error(f"Failed to initialize PostgresSaver: {str(e)}", exc_info=True)
        raise


def reset_checkpointer() -> None:
    """
    Reset the singleton checkpointer instance.

    This function is primarily for testing purposes, allowing tests to
    reset the singleton state between test runs.

    Warning:
        This should only be used in tests, not in production code.
    """
    global _checkpointer_instance
    _checkpointer_instance = None
