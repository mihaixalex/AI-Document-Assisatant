"""
PostgresSaver checkpointer module for conversation persistence.

This module provides a singleton AsyncPostgresSaver instance that enables
LangGraph state persistence across sessions using PostgreSQL.
"""

import asyncio
import logging
import os
from typing import Any, Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)

_checkpointer_instance: Optional[AsyncPostgresSaver] = None
_checkpointer_cm: Optional[Any] = None  # Async context manager
_lock = asyncio.Lock()


async def get_checkpointer() -> AsyncPostgresSaver:
    """
    Returns singleton AsyncPostgresSaver instance initialized from DATABASE_URL.

    Thread-safe async singleton pattern using asyncio.Lock with double-check locking.
    This ensures only one AsyncPostgresSaver instance is created even with concurrent calls.

    The checkpointer is obtained by entering an async context manager. The context manager
    reference is stored to allow proper cleanup via cleanup_checkpointer() on shutdown.

    AsyncPostgresSaver.setup() creates the following tables:
    - checkpoints: Stores graph state snapshots
    - checkpoint_writes: Stores pending writes

    These tables are separate from application tables (conversations, documents)
    managed by Alembic migrations.

    Returns:
        AsyncPostgresSaver: Singleton checkpointer instance

    Raises:
        ValueError: If DATABASE_URL environment variable is not set or initialization fails

    Example:
        >>> checkpointer = await get_checkpointer()
        >>> graph = builder.compile(checkpointer=checkpointer)
    """
    global _checkpointer_instance, _checkpointer_cm

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
            logger.info("Initializing AsyncPostgresSaver checkpointer")
            # AsyncPostgresSaver.from_conn_string returns an async context manager
            # We need to enter it with __aenter__() to get the actual checkpointer instance
            checkpointer_cm = AsyncPostgresSaver.from_conn_string(database_url)
            checkpointer = await checkpointer_cm.__aenter__()

            # Now call setup on the actual checkpointer instance
            await checkpointer.setup()

            # Store both the context manager and the checkpointer for proper lifecycle management
            # The context manager reference is needed for cleanup via __aexit__() on shutdown
            _checkpointer_cm = checkpointer_cm
            _checkpointer_instance = checkpointer
            logger.info("AsyncPostgresSaver checkpointer initialized successfully")
            return _checkpointer_instance
        except Exception as e:
            # Reset to None on failure to allow retry
            _checkpointer_instance = None
            _checkpointer_cm = None
            logger.error(f"Failed to initialize AsyncPostgresSaver: {str(e)}", exc_info=True)
            raise ValueError(
                f"Failed to initialize AsyncPostgresSaver: {e}. "
                "Verify DATABASE_URL is correct and the database is accessible."
            ) from e


async def cleanup_checkpointer() -> None:
    """
    Cleanup the checkpointer by exiting the async context manager.

    This function should be called during application shutdown to properly
    close database connections and cleanup resources.

    The function calls __aexit__() on the stored context manager to ensure
    proper cleanup of the connection pool.
    """
    global _checkpointer_instance, _checkpointer_cm
    async with _lock:
        if _checkpointer_cm is not None and _checkpointer_instance is not None:
            try:
                await _checkpointer_cm.__aexit__(None, None, None)
                logger.info("Checkpointer context manager exited successfully")
            except Exception as e:
                logger.warning(f"Error during checkpointer cleanup: {e}")
            finally:
                _checkpointer_instance = None
                _checkpointer_cm = None


async def reset_checkpointer() -> None:
    """
    Reset the singleton checkpointer instance (for testing only).

    This function should only be called in test environments to reset
    the singleton state between tests.

    Warning:
        Do not call this function in production code as it will invalidate
        the checkpointer instance and force reinitialization.
    """
    global _checkpointer_instance, _checkpointer_cm
    async with _lock:
        _checkpointer_instance = None
        _checkpointer_cm = None
        logger.info("Checkpointer instance reset")
