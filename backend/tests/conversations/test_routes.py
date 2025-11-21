"""Integration tests for conversation API routes.

Tests cover all 5 REST endpoints with comprehensive scenarios including
success cases, error handling, and edge cases. Uses pytest fixtures and
FastAPI TestClient for full HTTP integration testing.
"""

import uuid
from collections.abc import Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.conversations.repository import get_repository
from src.main import app


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create a mock repository instance."""
    return MagicMock()


@pytest.fixture
def client(mock_repository: MagicMock) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with mocked repository dependency."""
    app.dependency_overrides[get_repository] = lambda: mock_repository
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_conversation_data() -> dict:
    """Sample conversation data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "thread_id": "test-thread-123",
        "title": "Test Conversation",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "user_id": None,
        "is_deleted": False,
    }


class TestListConversations:
    """Tests for GET /api/conversations endpoint."""

    def test_list_conversations_success(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test listing conversations returns paginated results."""
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
        mock_repository.list_conversations = AsyncMock(return_value=(mock_conversations, 3))

        response = client.get("/api/conversations")

        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert len(data["conversations"]) == 3
        assert data["total"] == 3
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_list_conversations_with_pagination(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test listing conversations with custom limit and offset."""
        mock_repository.list_conversations = AsyncMock(return_value=([], 0))

        response = client.get("/api/conversations?limit=10&offset=20")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20

        # Verify repository was called with correct params
        mock_repository.list_conversations.assert_called_once_with(limit=10, offset=20)

    def test_list_conversations_validation_error(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test listing conversations with invalid parameters."""
        # Test limit out of range
        response = client.get("/api/conversations?limit=200")
        assert response.status_code == 422  # Validation error

        # Test negative offset
        response = client.get("/api/conversations?offset=-1")
        assert response.status_code == 422

    def test_list_conversations_repository_error(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test handling of repository errors."""
        mock_repository.list_conversations = AsyncMock(side_effect=Exception("Database error"))

        response = client.get("/api/conversations")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


class TestCreateConversation:
    """Tests for POST /api/conversations endpoint."""

    def test_create_conversation_success(
        self, client: TestClient, mock_repository: MagicMock, sample_conversation_data: dict
    ) -> None:
        """Test creating a new conversation."""
        mock_repository.create_conversation = AsyncMock(return_value=sample_conversation_data)

        response = client.post("/api/conversations", json={"title": "New Conversation"})

        assert response.status_code == 201
        data = response.json()
        assert data["threadId"] == "test-thread-123"
        assert data["title"] == "Test Conversation"
        assert "createdAt" in data
        assert "updatedAt" in data

    def test_create_conversation_without_title(
        self, client: TestClient, mock_repository: MagicMock, sample_conversation_data: dict
    ) -> None:
        """Test creating a conversation without a title."""
        conversation_without_title = {**sample_conversation_data, "title": None}
        mock_repository.create_conversation = AsyncMock(return_value=conversation_without_title)

        response = client.post("/api/conversations", json={})

        assert response.status_code == 201
        data = response.json()
        assert data["title"] is None
        assert data["threadId"] is not None

    def test_create_conversation_repository_error(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test handling of repository errors during creation."""
        mock_repository.create_conversation = AsyncMock(side_effect=Exception("Database error"))

        response = client.post("/api/conversations", json={"title": "New Conversation"})

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


class TestGetConversationHistory:
    """Tests for GET /api/conversations/{thread_id}/history endpoint."""

    @patch("src.retrieval_graph.graph.graph")
    def test_get_conversation_history_success(
        self,
        mock_graph: MagicMock,
        client: TestClient,
        mock_repository: MagicMock,
        sample_conversation_data: dict,
    ) -> None:
        """Test loading conversation history from checkpointer."""
        mock_repository.get_conversation = AsyncMock(return_value=sample_conversation_data)

        # Mock graph state with proper dict-based messages
        mock_state = MagicMock()
        # Return a dict message that can be serialized properly
        mock_message = {"content": "Hello, world!", "type": "human"}
        mock_state.values = {"messages": [mock_message]}
        mock_state.metadata = {"step": 1}

        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        response = client.get("/api/conversations/test-thread-123/history")

        assert response.status_code == 200
        data = response.json()
        assert data["threadId"] == "test-thread-123"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Hello, world!"
        assert data["metadata"]["step"] == 1

    def test_get_conversation_history_not_found(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test getting history for non-existent conversation."""
        mock_repository.get_conversation = AsyncMock(return_value=None)

        response = client.get("/api/conversations/non-existent/history")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_conversation_history_deleted(
        self, client: TestClient, mock_repository: MagicMock, sample_conversation_data: dict
    ) -> None:
        """Test getting history for deleted conversation."""
        deleted_conversation = {**sample_conversation_data, "is_deleted": True}
        mock_repository.get_conversation = AsyncMock(return_value=deleted_conversation)

        response = client.get("/api/conversations/test-thread-123/history")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch("src.retrieval_graph.graph.graph")
    def test_get_conversation_history_checkpoint_error(
        self,
        mock_graph: MagicMock,
        client: TestClient,
        mock_repository: MagicMock,
        sample_conversation_data: dict,
    ) -> None:
        """Test that checkpoint errors return empty state without crashing."""
        mock_repository.get_conversation = AsyncMock(return_value=sample_conversation_data)

        # Mock checkpoint failure
        mock_graph.aget_state = AsyncMock(side_effect=Exception("Checkpoint error"))

        response = client.get("/api/conversations/test-thread-123/history")

        # Should return 200 with empty messages (no crash)
        assert response.status_code == 200
        data = response.json()
        assert data["threadId"] == "test-thread-123"
        assert data["messages"] == []
        assert data["metadata"] == {}

    @patch("src.retrieval_graph.graph.graph")
    def test_get_conversation_history_empty_state(
        self,
        mock_graph: MagicMock,
        client: TestClient,
        mock_repository: MagicMock,
        sample_conversation_data: dict,
    ) -> None:
        """Test loading conversation history with no messages."""
        mock_repository.get_conversation = AsyncMock(return_value=sample_conversation_data)

        # Mock empty state
        mock_state = MagicMock()
        mock_state.values = {"messages": []}
        mock_state.metadata = {}

        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        response = client.get("/api/conversations/test-thread-123/history")

        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []

    @patch("src.retrieval_graph.graph.graph")
    def test_get_conversation_history_with_pydantic_messages(
        self,
        mock_graph: MagicMock,
        client: TestClient,
        mock_repository: MagicMock,
        sample_conversation_data: dict,
    ) -> None:
        """Test loading conversation history with Pydantic messages (hasattr dict)."""
        mock_repository.get_conversation = AsyncMock(return_value=sample_conversation_data)

        # Mock message with dict() method (Pydantic-like)
        mock_message = MagicMock()
        mock_message.dict.return_value = {"content": "Pydantic message", "type": "human"}

        mock_state = MagicMock()
        mock_state.values = {"messages": [mock_message]}
        mock_state.metadata = {}

        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        response = client.get("/api/conversations/test-thread-123/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Pydantic message"

    @patch("src.retrieval_graph.graph.graph")
    def test_get_conversation_history_with_langchain_messages(
        self,
        mock_graph: MagicMock,
        client: TestClient,
        mock_repository: MagicMock,
        sample_conversation_data: dict,
    ) -> None:
        """Test loading conversation history with LangChain-like messages."""
        mock_repository.get_conversation = AsyncMock(return_value=sample_conversation_data)

        # Mock message with content and type attributes (LangChain-like)
        mock_message = MagicMock(spec=["content", "type"])
        mock_message.content = "LangChain message"
        mock_message.type = "ai"
        # Ensure dict() method doesn't exist for this path
        delattr(mock_message, "dict")

        mock_state = MagicMock()
        mock_state.values = {"messages": [mock_message]}
        mock_state.metadata = {}

        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        response = client.get("/api/conversations/test-thread-123/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "LangChain message"
        assert data["messages"][0]["type"] == "ai"

    @patch("src.retrieval_graph.graph.graph")
    def test_get_conversation_history_with_unknown_messages(
        self,
        mock_graph: MagicMock,
        client: TestClient,
        mock_repository: MagicMock,
        sample_conversation_data: dict,
    ) -> None:
        """Test loading conversation history with unknown message types."""
        mock_repository.get_conversation = AsyncMock(return_value=sample_conversation_data)

        # Mock unknown message type (just a string)
        mock_state = MagicMock()
        mock_state.values = {"messages": ["unknown message type"]}
        mock_state.metadata = {}

        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        response = client.get("/api/conversations/test-thread-123/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "unknown message type"
        assert data["messages"][0]["type"] == "unknown"


class TestUpdateConversation:
    """Tests for PATCH /api/conversations/{thread_id} endpoint."""

    def test_update_conversation_success(
        self, client: TestClient, mock_repository: MagicMock, sample_conversation_data: dict
    ) -> None:
        """Test updating a conversation's title."""
        updated_conversation = {**sample_conversation_data, "title": "Updated Title"}
        mock_repository.update_conversation = AsyncMock(return_value=updated_conversation)

        response = client.patch(
            "/api/conversations/test-thread-123", json={"title": "Updated Title"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["threadId"] == "test-thread-123"

    def test_update_conversation_not_found(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test updating a non-existent conversation."""
        mock_repository.update_conversation = AsyncMock(return_value=None)

        response = client.patch("/api/conversations/non-existent", json={"title": "New Title"})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_conversation_validation_error(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test updating conversation with invalid data."""
        # Test empty title
        response = client.patch("/api/conversations/test-thread-123", json={"title": ""})
        assert response.status_code == 422

        # Test missing title
        response = client.patch("/api/conversations/test-thread-123", json={})
        assert response.status_code == 422

    def test_update_conversation_repository_error(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test handling of repository errors during update."""
        mock_repository.update_conversation = AsyncMock(side_effect=Exception("Database error"))

        response = client.patch("/api/conversations/test-thread-123", json={"title": "New Title"})

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


class TestDeleteConversation:
    """Tests for DELETE /api/conversations/{thread_id} endpoint."""

    def test_delete_conversation_success(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test soft deleting a conversation."""
        mock_repository.soft_delete_conversation = AsyncMock(return_value=True)

        response = client.delete("/api/conversations/test-thread-123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["threadId"] == "test-thread-123"
        assert "deleted successfully" in data["message"]

    def test_delete_conversation_not_found(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test deleting a non-existent conversation."""
        mock_repository.soft_delete_conversation = AsyncMock(return_value=False)

        response = client.delete("/api/conversations/non-existent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_delete_conversation_repository_error(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test handling of repository errors during deletion."""
        mock_repository.soft_delete_conversation = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = client.delete("/api/conversations/test-thread-123")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]
