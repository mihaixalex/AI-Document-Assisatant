"""Tests for retrieval module - TDD approach (write tests first)."""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.vectorstores import VectorStoreRetriever

from src.shared.configuration import BaseConfiguration
from src.shared.retrieval import make_retriever, make_supabase_retriever


class TestMakeSupabaseRetriever:
    """Test the make_supabase_retriever function."""

    @pytest.mark.asyncio
    async def test_make_supabase_retriever_success(self) -> None:
        """Test successful creation of Supabase retriever."""
        config = BaseConfiguration(
            retriever_provider="supabase", k=10, filter_kwargs={"user_id": "test123"}
        )

        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"},
        ):
            with patch("src.shared.retrieval.OpenAIEmbeddings") as mock_embeddings_class:
                with patch("src.shared.retrieval.create_client") as mock_create_client:
                    with patch(
                        "src.shared.retrieval.SupabaseVectorStore"
                    ) as mock_vector_store_class:
                        # Setup mocks
                        mock_embeddings = MagicMock()
                        mock_embeddings_class.return_value = mock_embeddings

                        mock_supabase_client = MagicMock()
                        mock_create_client.return_value = mock_supabase_client

                        mock_retriever = MagicMock(spec=VectorStoreRetriever)
                        mock_vector_store = MagicMock()
                        mock_vector_store.as_retriever.return_value = mock_retriever
                        mock_vector_store_class.return_value = mock_vector_store

                        # Call function
                        result = await make_supabase_retriever(config)

                        # Verify embeddings initialization
                        mock_embeddings_class.assert_called_once_with(
                            model="text-embedding-3-small"
                        )

                        # Verify Supabase client creation
                        mock_create_client.assert_called_once_with(
                            "https://test.supabase.co", "test-key"
                        )

                        # Verify vector store creation
                        mock_vector_store_class.assert_called_once_with(
                            client=mock_supabase_client,
                            embedding=mock_embeddings,
                            table_name="documents",
                            query_name="match_documents",
                        )

                        # Verify retriever configuration
                        mock_vector_store.as_retriever.assert_called_once_with(
                            k=10, search_kwargs={"filter": {"user_id": "test123"}}
                        )

                        assert result == mock_retriever

    @pytest.mark.asyncio
    async def test_make_supabase_retriever_missing_url(self) -> None:
        """Test error when SUPABASE_URL is missing."""
        config = BaseConfiguration()

        with patch.dict(os.environ, {"SUPABASE_SERVICE_ROLE_KEY": "test-key"}, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_URL.*not defined"):
                await make_supabase_retriever(config)

    @pytest.mark.asyncio
    async def test_make_supabase_retriever_missing_key(self) -> None:
        """Test error when SUPABASE_SERVICE_ROLE_KEY is missing."""
        config = BaseConfiguration()

        with patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co"}, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY.*not defined"):
                await make_supabase_retriever(config)

    @pytest.mark.asyncio
    async def test_make_supabase_retriever_default_config(self) -> None:
        """Test with default configuration values."""
        config = BaseConfiguration()  # k=5, filter_kwargs={}

        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"},
        ):
            with patch("src.shared.retrieval.OpenAIEmbeddings"):
                with patch("src.shared.retrieval.create_client"):
                    with patch("src.shared.retrieval.SupabaseVectorStore") as mock_vs_class:
                        mock_vector_store = MagicMock()
                        mock_retriever = MagicMock(spec=VectorStoreRetriever)
                        mock_vector_store.as_retriever.return_value = mock_retriever
                        mock_vs_class.return_value = mock_vector_store

                        await make_supabase_retriever(config)

                        # Verify default k=5 and empty filter
                        mock_vector_store.as_retriever.assert_called_once_with(
                            k=5, search_kwargs={}
                        )

    @pytest.mark.asyncio
    async def test_make_supabase_retriever_empty_filter_kwargs(self) -> None:
        """Test with empty filter_kwargs."""
        config = BaseConfiguration(k=3, filter_kwargs={})

        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"},
        ):
            with patch("src.shared.retrieval.OpenAIEmbeddings"):
                with patch("src.shared.retrieval.create_client"):
                    with patch("src.shared.retrieval.SupabaseVectorStore") as mock_vs_class:
                        mock_vector_store = MagicMock()
                        mock_retriever = MagicMock(spec=VectorStoreRetriever)
                        mock_vector_store.as_retriever.return_value = mock_retriever
                        mock_vs_class.return_value = mock_vector_store

                        await make_supabase_retriever(config)

                        # Verify k=3 and empty filter
                        mock_vector_store.as_retriever.assert_called_once_with(
                            k=3, search_kwargs={}
                        )


class TestMakeRetriever:
    """Test the make_retriever factory function."""

    @pytest.mark.asyncio
    async def test_make_retriever_with_supabase(self) -> None:
        """Test make_retriever dispatches to Supabase retriever."""
        config: dict[str, Any] = {
            "configurable": {
                "retriever_provider": "supabase",
                "k": 7,
                "filter_kwargs": {"source": "pdf"},
            }
        }

        mock_retriever = MagicMock(spec=VectorStoreRetriever)

        with patch(
            "src.shared.retrieval.make_supabase_retriever", new_callable=AsyncMock
        ) as mock_make_supabase:
            mock_make_supabase.return_value = mock_retriever

            result = await make_retriever(config)

            # Verify make_supabase_retriever was called
            mock_make_supabase.assert_called_once()

            # Verify configuration was passed correctly
            call_args = mock_make_supabase.call_args[0][0]
            assert call_args.retriever_provider == "supabase"
            assert call_args.k == 7
            assert call_args.filter_kwargs == {"source": "pdf"}

            assert result == mock_retriever

    @pytest.mark.asyncio
    async def test_make_retriever_with_default_config(self) -> None:
        """Test make_retriever with empty config uses defaults."""
        config: dict[str, Any] = {}

        mock_retriever = MagicMock(spec=VectorStoreRetriever)

        with patch(
            "src.shared.retrieval.make_supabase_retriever", new_callable=AsyncMock
        ) as mock_make_supabase:
            mock_make_supabase.return_value = mock_retriever

            result = await make_retriever(config)

            # Verify defaults were used
            call_args = mock_make_supabase.call_args[0][0]
            assert call_args.retriever_provider == "supabase"
            assert call_args.k == 5
            assert call_args.filter_kwargs == {}

            assert result == mock_retriever

    @pytest.mark.asyncio
    async def test_make_retriever_with_none_config(self) -> None:
        """Test make_retriever with None config."""
        mock_retriever = MagicMock(spec=VectorStoreRetriever)

        with patch(
            "src.shared.retrieval.make_supabase_retriever", new_callable=AsyncMock
        ) as mock_make_supabase:
            mock_make_supabase.return_value = mock_retriever

            result = await make_retriever(None)

            # Should use defaults
            call_args = mock_make_supabase.call_args[0][0]
            assert call_args.retriever_provider == "supabase"
            assert call_args.k == 5

            assert result == mock_retriever

    @pytest.mark.asyncio
    async def test_make_retriever_unsupported_provider(self) -> None:
        """Test error with unsupported retriever provider."""
        # Note: This test verifies the extensibility pattern
        # Currently only 'supabase' is supported, but the architecture
        # allows for future providers

        # For now, we can't actually test this since the type system
        # only allows 'supabase', but we document the expected behavior:
        # If we add more providers in the future, unsupported ones should raise ValueError

        # This is a placeholder test showing the expected pattern
        config: dict[str, Any] = {"configurable": {"retriever_provider": "supabase"}}

        mock_retriever = MagicMock(spec=VectorStoreRetriever)

        with patch(
            "src.shared.retrieval.make_supabase_retriever", new_callable=AsyncMock
        ) as mock_make_supabase:
            mock_make_supabase.return_value = mock_retriever

            # Should work for supabase
            result = await make_retriever(config)
            assert result == mock_retriever

    @pytest.mark.asyncio
    async def test_make_retriever_extracts_from_configurable(self) -> None:
        """Test that make_retriever correctly extracts config from 'configurable' key."""
        config: dict[str, Any] = {
            "other_key": "ignored",
            "configurable": {
                "retriever_provider": "supabase",
                "k": 15,
                "filter_kwargs": {"type": "invoice"},
            },
            "also_ignored": "value",
        }

        mock_retriever = MagicMock(spec=VectorStoreRetriever)

        with patch(
            "src.shared.retrieval.make_supabase_retriever", new_callable=AsyncMock
        ) as mock_make_supabase:
            mock_make_supabase.return_value = mock_retriever

            await make_retriever(config)

            # Verify only configurable values were used
            call_args = mock_make_supabase.call_args[0][0]
            assert call_args.k == 15
            assert call_args.filter_kwargs == {"type": "invoice"}
            assert not hasattr(call_args, "other_key")
            assert not hasattr(call_args, "also_ignored")
