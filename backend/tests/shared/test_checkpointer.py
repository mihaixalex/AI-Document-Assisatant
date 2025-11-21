"""Tests for PostgresSaver checkpointer module.

This module tests the checkpointer singleton pattern, initialization,
and integration with LangGraph state management.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.checkpoint.postgres import PostgresSaver

from src.shared.checkpointer import get_checkpointer, reset_checkpointer


@pytest.fixture(autouse=True)
async def reset_singleton():
    """Reset checkpointer singleton before each test."""
    await reset_checkpointer()
    yield
    await reset_checkpointer()


@pytest.fixture
def mock_database_url(monkeypatch):
    """Set DATABASE_URL environment variable for tests."""
    test_db_url = "postgresql://user:pass@localhost:5432/testdb"
    monkeypatch.setenv("DATABASE_URL", test_db_url)
    return test_db_url


@pytest.fixture
def mock_postgres_saver():
    """Create a mock PostgresSaver instance."""
    mock_saver = MagicMock(spec=PostgresSaver)
    mock_saver.setup = AsyncMock()
    return mock_saver


class TestGetCheckpointer:
    """Tests for get_checkpointer function."""

    @pytest.mark.asyncio
    async def test_get_checkpointer_success(self, mock_database_url, mock_postgres_saver):
        """Test successful checkpointer initialization."""
        with patch(
            "src.shared.checkpointer.PostgresSaver.from_conn_string",
            return_value=mock_postgres_saver,
        ) as mock_from_conn:
            checkpointer = await get_checkpointer()

            # Verify PostgresSaver was created with correct URL
            mock_from_conn.assert_called_once_with(mock_database_url)

            # Verify setup was called
            mock_postgres_saver.setup.assert_called_once()

            # Verify correct instance returned
            assert checkpointer is mock_postgres_saver

    @pytest.mark.asyncio
    async def test_get_checkpointer_singleton_pattern(
        self, mock_database_url, mock_postgres_saver
    ):
        """Test that get_checkpointer returns the same instance on multiple calls."""
        with patch(
            "src.shared.checkpointer.PostgresSaver.from_conn_string",
            return_value=mock_postgres_saver,
        ):
            checkpointer1 = await get_checkpointer()
            checkpointer2 = await get_checkpointer()

            # Verify same instance
            assert checkpointer1 is checkpointer2

            # Verify setup only called once
            assert mock_postgres_saver.setup.call_count == 1

    @pytest.mark.asyncio
    async def test_get_checkpointer_missing_database_url(self, monkeypatch):
        """Test that get_checkpointer raises ValueError when DATABASE_URL is not set."""
        # Remove DATABASE_URL from environment
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(ValueError, match="DATABASE_URL environment variable is required"):
            await get_checkpointer()

    @pytest.mark.asyncio
    async def test_get_checkpointer_setup_failure(self, mock_database_url):
        """Test that initialization errors are propagated correctly."""
        mock_saver = MagicMock(spec=PostgresSaver)
        mock_saver.setup = AsyncMock(side_effect=Exception("Database connection failed"))

        with patch(
            "src.shared.checkpointer.PostgresSaver.from_conn_string", return_value=mock_saver
        ):
            with pytest.raises(Exception, match="Database connection failed"):
                await get_checkpointer()

    @pytest.mark.asyncio
    async def test_get_checkpointer_from_conn_string_failure(self, mock_database_url):
        """Test that from_conn_string errors are propagated correctly."""
        with patch(
            "src.shared.checkpointer.PostgresSaver.from_conn_string",
            side_effect=Exception("Invalid connection string"),
        ):
            with pytest.raises(Exception, match="Invalid connection string"):
                await get_checkpointer()


class TestResetCheckpointer:
    """Tests for reset_checkpointer function."""

    @pytest.mark.asyncio
    async def test_reset_checkpointer_clears_singleton(
        self, mock_database_url, mock_postgres_saver
    ):
        """Test that reset_checkpointer clears the singleton instance."""
        with patch(
            "src.shared.checkpointer.PostgresSaver.from_conn_string",
            return_value=mock_postgres_saver,
        ):
            # Get initial instance
            checkpointer1 = await get_checkpointer()

            # Reset singleton
            await reset_checkpointer()

            # Get new instance
            checkpointer2 = await get_checkpointer()

            # Verify different instances
            # (In mock, they'll be the same mock object, but setup will be called twice)
            assert mock_postgres_saver.setup.call_count == 2


@pytest.mark.integration
class TestCheckpointerIntegration:
    """Integration tests for checkpointer with real PostgresSaver.

    These tests require a valid DATABASE_URL to be set and will create
    real database connections. They are marked as integration tests
    and can be skipped with: pytest -m "not integration"
    """

    @pytest.mark.asyncio
    async def test_checkpointer_real_initialization(self):
        """Test checkpointer initialization with real PostgresSaver.

        This test requires DATABASE_URL to be set to a valid PostgreSQL connection string.
        """
        # Skip if DATABASE_URL not set
        if not os.environ.get("DATABASE_URL"):
            pytest.skip("DATABASE_URL not set, skipping integration test")

        # Reset singleton to ensure clean state
        await reset_checkpointer()

        try:
            # Get checkpointer
            checkpointer = await get_checkpointer()

            # Verify it's a PostgresSaver instance
            assert isinstance(checkpointer, PostgresSaver)

            # Verify singleton pattern
            checkpointer2 = await get_checkpointer()
            assert checkpointer is checkpointer2

        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")

    @pytest.mark.asyncio
    async def test_checkpointer_with_graph_compilation(self):
        """Test checkpointer integration with LangGraph compilation.

        This test verifies that the checkpointer can be used to compile
        a LangGraph graph with persistence enabled.
        """
        # Skip if DATABASE_URL not set
        if not os.environ.get("DATABASE_URL"):
            pytest.skip("DATABASE_URL not set, skipping integration test")

        # Reset singleton
        await reset_checkpointer()

        try:
            # Import graph modules
            from src.retrieval_graph.graph import compile_with_checkpointer

            # Compile graph with checkpointer
            graph = await compile_with_checkpointer()

            # Verify graph is compiled
            assert graph is not None

            # Verify graph has checkpointer
            assert graph.checkpointer is not None

        except Exception as e:
            pytest.fail(f"Graph compilation integration test failed: {e}")

    @pytest.mark.asyncio
    async def test_checkpointer_checkpoint_persistence(self):
        """Test that checkpointer can save and retrieve checkpoints.

        This test verifies the full checkpoint write/read cycle.
        """
        # Skip if DATABASE_URL not set
        if not os.environ.get("DATABASE_URL"):
            pytest.skip("DATABASE_URL not set, skipping integration test")

        # Reset singleton
        await reset_checkpointer()

        try:
            from langchain_core.runnables import RunnableConfig

            # Get checkpointer
            checkpointer = await get_checkpointer()

            # Create a test checkpoint
            test_config = RunnableConfig(configurable={"thread_id": "test-thread-123"})
            test_state = {
                "messages": ["Hello"],
                "query": "Test query",
                "route": "retrieve",
                "documents": [],
            }

            # Save checkpoint
            await checkpointer.aput(
                config=test_config,
                checkpoint={
                    "v": 1,
                    "ts": "2024-01-01T00:00:00Z",
                    "id": "checkpoint-1",
                    "channel_values": test_state,
                    "channel_versions": {},
                    "versions_seen": {},
                },
                metadata={"step": 1},
            )

            # Retrieve checkpoint
            retrieved = await checkpointer.aget(test_config)

            # Verify checkpoint was saved and retrieved
            assert retrieved is not None
            assert "channel_values" in retrieved

        except Exception as e:
            pytest.fail(f"Checkpoint persistence test failed: {e}")


class TestCheckpointerErrorHandling:
    """Tests for checkpointer error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_get_checkpointer_with_invalid_url(self, monkeypatch):
        """Test error handling with invalid database URL."""
        monkeypatch.setenv("DATABASE_URL", "invalid://url")

        with patch(
            "src.shared.checkpointer.PostgresSaver.from_conn_string",
            side_effect=ValueError("Invalid connection string format"),
        ):
            with pytest.raises(ValueError, match="Invalid connection string format"):
                await get_checkpointer()

    @pytest.mark.asyncio
    async def test_get_checkpointer_concurrent_calls(self, mock_database_url, mock_postgres_saver):
        """Test that concurrent calls to get_checkpointer don't create multiple instances."""
        import asyncio

        with patch(
            "src.shared.checkpointer.PostgresSaver.from_conn_string",
            return_value=mock_postgres_saver,
        ):
            # Call get_checkpointer concurrently
            results = await asyncio.gather(
                get_checkpointer(), get_checkpointer(), get_checkpointer()
            )

            # Verify all results are the same instance
            assert results[0] is results[1]
            assert results[1] is results[2]

            # Verify setup only called once
            assert mock_postgres_saver.setup.call_count == 1
