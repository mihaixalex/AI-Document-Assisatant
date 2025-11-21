"""
PostgresSaver checkpointer module for conversation persistence.

This module provides a singleton PostgresSaver instance that enables
LangGraph state persistence across sessions using PostgreSQL.
"""

import asyncio
import logging
import os
from typing import Optional

from langgraph.checkpoint.postgres import PostgresSaver

logger = logging.getLogger(__name__)

_checkpointer_instance: Optional[PostgresSaver] = None
_lock = asyncio.Lock()


async def get_checkpointer() -> PostgresSaver:
    """
    Returns singleton PostgresSaver instance initialized from DATABASE_URL.

    Thread-safe async singleton pattern using asyncio.Lock with double-check locking.
    This ensures only one PostgresSaver instance is created even with concurrent calls.

    PostgresSaver.setup() creates the following tables:
    - checkpoints: Stores graph state snapshots
    - checkpoint_writes: Stores pending writes

    These tables are separate from application tables (conversations, documents)
    managed by Alembic migrations.

    Returns:
        PostgresSaver: Singleton checkpointer instance

    Raises:
        ValueError: If DATABASE_URL environment variable is not set or initialization fails

    Example:
        >>> checkpointer = await get_checkpointer()
        >>> graph = builder.compile(checkpointer=checkpointer)
    """
    global _checkpointer_instance

    # Fast path: return existing instance without acquiring lock
    if _checkpointer_instance is not None:
        return _checkpointer_instance

    # Slow path: acquire lock and initialize
    async with _lock:
        # Double-check pattern: recheck after acquiring lock
        if _checkpointer_instance is not None:
            return _checkpointer_instance

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required for conversation persistence"
            )

        try:
            logger.info("Initializing PostgresSaver checkpointer")
            checkpointer = PostgresSaver.from_conn_string(database_url)
            await checkpointer.setup()
            _checkpointer_instance = checkpointer
            logger.info("PostgresSaver checkpointer initialized successfully")
            return _checkpointer_instance
        except Exception as e:
            # Reset to None on failure to allow retry
            _checkpointer_instance = None
            logger.error(f"Failed to initialize PostgresSaver: {str(e)}", exc_info=True)
            raise ValueError(
                f"Failed to initialize PostgresSaver: {e}. "
                "Verify DATABASE_URL is correct and the database is accessible."
            ) from e


async def reset_checkpointer() -> None:
    """
    Reset the singleton checkpointer instance (for testing only).

    This function should only be called in test environments to reset
    the singleton state between tests.

    Warning:
        Do not call this function in production code as it will invalidate
        the checkpointer instance and force reinitialization.
    """
    global _checkpointer_instance
    async with _lock:
        _checkpointer_instance = None
        logger.info("Checkpointer instance reset")
