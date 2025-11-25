"""Repository layer for conversation database operations.

This module implements the repository pattern for CRUD operations on the
conversations table. It uses psycopg3 for direct PostgreSQL access and follows
async/await patterns for non-blocking I/O.
"""

import logging
import os
import uuid
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


class ConversationRepository:
    """Repository for conversation database operations.

    This class provides CRUD operations for the conversations table with:
    - Server-generated UUIDs for thread_id
    - Soft delete pattern (is_deleted flag)
    - Async operations using psycopg3
    """

    def __init__(self, database_url: str) -> None:
        """Initialize repository with database connection string.

        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        self._pool: AsyncConnectionPool | None = None

    async def _get_pool(self) -> AsyncConnectionPool:
        """Get or create the connection pool.

        Returns:
            AsyncConnectionPool instance
        """
        if self._pool is None:
            self._pool = AsyncConnectionPool(
                self.database_url,
                min_size=2,
                max_size=10,
                kwargs={"row_factory": dict_row},
                open=False,  # Explicit: pool must be opened before use
            )
            await self._pool.open()  # Open the pool
        return self._pool

    async def list_conversations(
        self, limit: int = 50, offset: int = 0, include_deleted: bool = False
    ) -> tuple[list[dict[str, Any]], int]:
        """List conversations with pagination.

        Args:
            limit: Maximum number of conversations to return (default 50)
            offset: Number of conversations to skip (default 0)
            include_deleted: Whether to include soft-deleted conversations (default False)

        Returns:
            Tuple of (conversations list, total count)
        """
        pool = await self._get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Use static queries to prevent SQL injection
                if include_deleted:
                    count_query = "SELECT COUNT(*) as count FROM conversations"
                    list_query = """
                        SELECT id, thread_id, title, created_at, updated_at, user_id, is_deleted
                        FROM conversations
                        ORDER BY updated_at DESC
                        LIMIT %s OFFSET %s
                    """
                else:
                    count_query = (
                        "SELECT COUNT(*) as count FROM conversations WHERE is_deleted = false"
                    )
                    list_query = """
                        SELECT id, thread_id, title, created_at, updated_at, user_id, is_deleted
                        FROM conversations
                        WHERE is_deleted = false
                        ORDER BY updated_at DESC
                        LIMIT %s OFFSET %s
                    """

                # Get total count
                await cur.execute(count_query)
                count_result = await cur.fetchone()
                total = count_result["count"] if count_result else 0

                # Get paginated results
                await cur.execute(list_query, (limit, offset))
                conversations = await cur.fetchall()

                return (list(conversations), total)

    async def create_conversation(self, title: str | None = None) -> dict[str, Any]:
        """Create a new conversation with server-generated thread_id.

        Args:
            title: Optional conversation title

        Returns:
            Created conversation record as dict
        """
        # Generate server-side UUID for thread_id
        thread_id = str(uuid.uuid4())

        pool = await self._get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                try:
                    query = """
                        INSERT INTO conversations (thread_id, title, created_at, updated_at, is_deleted)
                        VALUES (%s, %s, NOW(), NOW(), false)
                        RETURNING id, thread_id, title, created_at, updated_at, user_id, is_deleted
                    """
                    await cur.execute(query, (thread_id, title))
                    result = await cur.fetchone()

                    if not result:
                        raise ValueError("Failed to create conversation")

                    await conn.commit()
                    return dict(result)
                except Exception as e:
                    await conn.rollback()
                    logger.error("Failed to create conversation: %s", e)
                    raise

    async def get_conversation(self, thread_id: str) -> dict[str, Any] | None:
        """Get a conversation by thread_id.

        Args:
            thread_id: LangGraph thread identifier

        Returns:
            Conversation record as dict or None if not found
        """
        pool = await self._get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                query = """
                    SELECT id, thread_id, title, created_at, updated_at, user_id, is_deleted
                    FROM conversations
                    WHERE thread_id = %s
                """
                await cur.execute(query, (thread_id,))
                result = await cur.fetchone()
                return dict(result) if result else None

    async def update_conversation(self, thread_id: str, title: str) -> dict[str, Any] | None:
        """Update a conversation's title.

        Args:
            thread_id: LangGraph thread identifier
            title: New conversation title

        Returns:
            Updated conversation record as dict or None if not found
        """
        pool = await self._get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                try:
                    query = """
                        UPDATE conversations
                        SET title = %s, updated_at = NOW()
                        WHERE thread_id = %s AND is_deleted = false
                        RETURNING id, thread_id, title, created_at, updated_at, user_id, is_deleted
                    """
                    await cur.execute(query, (title, thread_id))
                    result = await cur.fetchone()

                    await conn.commit()
                    return dict(result) if result else None
                except Exception as e:
                    await conn.rollback()
                    logger.error("Failed to update conversation: %s", e)
                    raise

    async def soft_delete_conversation(self, thread_id: str) -> bool:
        """Soft delete a conversation by setting is_deleted flag.

        Args:
            thread_id: LangGraph thread identifier

        Returns:
            True if conversation was deleted, False if not found
        """
        pool = await self._get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                try:
                    query = """
                        UPDATE conversations
                        SET is_deleted = true, updated_at = NOW()
                        WHERE thread_id = %s AND is_deleted = false
                        RETURNING id
                    """
                    await cur.execute(query, (thread_id,))
                    result = await cur.fetchone()

                    await conn.commit()
                    return result is not None
                except Exception as e:
                    await conn.rollback()
                    logger.error("Failed to delete conversation: %s", e)
                    raise

    async def close(self) -> None:
        """Close the connection pool and release resources."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


def get_repository() -> ConversationRepository:
    """Factory function to create a ConversationRepository instance.

    Returns:
        ConversationRepository instance configured with DATABASE_URL

    Raises:
        ValueError: If DATABASE_URL environment variable is not set
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is required for conversation persistence"
        )
    return ConversationRepository(database_url)
