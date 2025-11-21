"""Unit tests for ConversationRepository.

Tests cover all CRUD operations with mocked database connections
to ensure unit tests run fast without requiring a real database.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.conversations.repository import ConversationRepository, get_repository


class TestConversationRepository:
    """Unit tests for ConversationRepository class."""

    @pytest.fixture
    def repository(self) -> ConversationRepository:
        """Create a repository instance with a test database URL."""
        return ConversationRepository("postgresql://test:test@localhost:5432/test")

    @pytest.fixture
    def mock_connection(self) -> MagicMock:
        """Create a mock database connection."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.__aexit__.return_value = AsyncMock()
        return mock_conn

    @pytest.fixture
    def sample_conversation(self) -> dict:
        """Sample conversation record."""
        return {
            "id": uuid.uuid4(),
            "thread_id": "test-thread-123",
            "title": "Test Conversation",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "user_id": None,
            "is_deleted": False,
        }

    @pytest.mark.asyncio
    async def test_list_conversations_success(self, repository: ConversationRepository) -> None:
        """Test listing conversations with pagination."""
        mock_conversations = [
            {
                "id": uuid.uuid4(),
                "thread_id": f"thread-{i}",
                "title": f"Conversation {i}",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "user_id": None,
                "is_deleted": False,
            }
            for i in range(3)
        ]

        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            # Mock cursor methods
            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value={"count": 3})
            mock_cursor.fetchall = AsyncMock(return_value=mock_conversations)

            # Mock connection context managers
            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            # Call repository method
            conversations, total = await repository.list_conversations(limit=10, offset=0)

            # Verify results
            assert len(conversations) == 3
            assert total == 3
            assert conversations[0]["thread_id"] == "thread-0"

            # Verify queries were executed
            assert mock_cursor.execute.call_count == 2  # COUNT + SELECT

    @pytest.mark.asyncio
    async def test_list_conversations_with_deleted(
        self, repository: ConversationRepository
    ) -> None:
        """Test listing conversations includes deleted when requested."""
        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value={"count": 5})
            mock_cursor.fetchall = AsyncMock(return_value=[])

            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            # Call with include_deleted=True
            conversations, total = await repository.list_conversations(
                limit=10, offset=0, include_deleted=True
            )

            # Verify no WHERE clause was used
            execute_calls = mock_cursor.execute.call_args_list
            count_query = execute_calls[0][0][0]
            assert "WHERE is_deleted = false" not in count_query

    @pytest.mark.asyncio
    async def test_create_conversation_success(
        self, repository: ConversationRepository, sample_conversation: dict
    ) -> None:
        """Test creating a new conversation."""
        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=sample_conversation)
            mock_conn.commit = AsyncMock()

            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            # Create conversation
            result = await repository.create_conversation(title="Test Conversation")

            # Verify result
            assert result["thread_id"] == "test-thread-123"
            assert result["title"] == "Test Conversation"

            # Verify INSERT was executed
            mock_cursor.execute.assert_called_once()
            insert_query = mock_cursor.execute.call_args[0][0]
            assert "INSERT INTO conversations" in insert_query
            assert mock_conn.commit.called

    @pytest.mark.asyncio
    async def test_create_conversation_without_title(
        self, repository: ConversationRepository
    ) -> None:
        """Test creating a conversation without a title."""
        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            new_conversation = {
                "id": uuid.uuid4(),
                "thread_id": "generated-uuid",
                "title": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "user_id": None,
                "is_deleted": False,
            }

            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=new_conversation)
            mock_conn.commit = AsyncMock()

            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            result = await repository.create_conversation(title=None)

            assert result["title"] is None
            assert result["thread_id"] is not None

    @pytest.mark.asyncio
    async def test_get_conversation_success(
        self, repository: ConversationRepository, sample_conversation: dict
    ) -> None:
        """Test getting a conversation by thread_id."""
        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=sample_conversation)

            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            result = await repository.get_conversation("test-thread-123")

            assert result is not None
            assert result["thread_id"] == "test-thread-123"
            assert result["title"] == "Test Conversation"

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, repository: ConversationRepository) -> None:
        """Test getting a non-existent conversation."""
        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=None)

            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            result = await repository.get_conversation("non-existent")

            assert result is None

    @pytest.mark.asyncio
    async def test_update_conversation_success(
        self, repository: ConversationRepository, sample_conversation: dict
    ) -> None:
        """Test updating a conversation's title."""
        updated_conversation = {**sample_conversation, "title": "Updated Title"}

        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=updated_conversation)
            mock_conn.commit = AsyncMock()

            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            result = await repository.update_conversation("test-thread-123", "Updated Title")

            assert result is not None
            assert result["title"] == "Updated Title"
            assert mock_conn.commit.called

    @pytest.mark.asyncio
    async def test_update_conversation_not_found(self, repository: ConversationRepository) -> None:
        """Test updating a non-existent conversation."""
        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=None)
            mock_conn.commit = AsyncMock()

            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            result = await repository.update_conversation("non-existent", "New Title")

            assert result is None

    @pytest.mark.asyncio
    async def test_soft_delete_conversation_success(
        self, repository: ConversationRepository
    ) -> None:
        """Test soft deleting a conversation."""
        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value={"id": uuid.uuid4()})
            mock_conn.commit = AsyncMock()

            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            result = await repository.soft_delete_conversation("test-thread-123")

            assert result is True
            assert mock_conn.commit.called

            # Verify UPDATE was executed with is_deleted = true
            update_query = mock_cursor.execute.call_args[0][0]
            assert "UPDATE conversations" in update_query
            assert "is_deleted = true" in update_query

    @pytest.mark.asyncio
    async def test_soft_delete_conversation_not_found(
        self, repository: ConversationRepository
    ) -> None:
        """Test soft deleting a non-existent conversation."""
        with patch("psycopg.AsyncConnection.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=None)
            mock_conn.commit = AsyncMock()

            mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = AsyncMock()

            mock_connect.return_value = mock_conn

            result = await repository.soft_delete_conversation("non-existent")

            assert result is False


class TestGetRepository:
    """Tests for get_repository factory function."""

    def test_get_repository_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test factory function with valid DATABASE_URL."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

        repository = get_repository()

        assert isinstance(repository, ConversationRepository)
        assert repository.database_url == "postgresql://test:test@localhost:5432/test"

    def test_get_repository_missing_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test factory function raises error when DATABASE_URL is missing."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(ValueError, match="DATABASE_URL environment variable is required"):
            get_repository()
