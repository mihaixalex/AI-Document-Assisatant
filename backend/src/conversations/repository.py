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
        async with await psycopg.AsyncConnection.connect(
            self.database_url, row_factory=dict_row
        ) as conn:
            async with conn.cursor() as cur:
                # Build WHERE clause
                where_clause = "" if include_deleted else "WHERE is_deleted = false"

                # Get total count
                count_query = f"SELECT COUNT(*) as count FROM conversations {where_clause}"
                await cur.execute(count_query)
                count_result = await cur.fetchone()
                total = count_result["count"] if count_result else 0

                # Get paginated results ordered by updated_at DESC
                list_query = f"""
                    SELECT id, thread_id, title, created_at, updated_at, user_id, is_deleted
                    FROM conversations
                    {where_clause}
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                """
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

        async with await psycopg.AsyncConnection.connect(
            self.database_url, row_factory=dict_row
        ) as conn:
            async with conn.cursor() as cur:
                query = """
                    INSERT INTO conversations (thread_id, title, created_at, updated_at, is_deleted)
                    VALUES (%s, %s, NOW(), NOW(), false)
                    RETURNING id, thread_id, title, created_at, updated_at, user_id, is_deleted
                """
                await cur.execute(query, (thread_id, title))
                result = await cur.fetchone()
                await conn.commit()

                if not result:
                    raise ValueError("Failed to create conversation")

                return dict(result)

    async def get_conversation(self, thread_id: str) -> dict[str, Any] | None:
        """Get a conversation by thread_id.

        Args:
            thread_id: LangGraph thread identifier

        Returns:
            Conversation record as dict or None if not found
        """
        async with await psycopg.AsyncConnection.connect(
            self.database_url, row_factory=dict_row
        ) as conn:
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
        async with await psycopg.AsyncConnection.connect(
            self.database_url, row_factory=dict_row
        ) as conn:
            async with conn.cursor() as cur:
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

    async def soft_delete_conversation(self, thread_id: str) -> bool:
        """Soft delete a conversation by setting is_deleted flag.

        Args:
            thread_id: LangGraph thread identifier

        Returns:
            True if conversation was deleted, False if not found
        """
        async with await psycopg.AsyncConnection.connect(
            self.database_url, row_factory=dict_row
        ) as conn:
            async with conn.cursor() as cur:
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
