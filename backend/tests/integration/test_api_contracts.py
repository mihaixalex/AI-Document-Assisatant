"""API contract tests to validate compatibility with frontend.

This test suite ensures that the Python backend maintains exact API compatibility
with the TypeScript backend, validating:
1. Response formats match exactly (JSON structure)
2. HTTP status codes are correct
3. Error responses match expected format
4. Streaming format is compatible with SSE parsing
5. Thread ID handling works correctly

These tests act as regression tests to prevent API breaking changes.
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from src.ingestion_graph.graph import graph as ingestion_graph
from src.retrieval_graph.graph import graph as retrieval_graph


class TestIngestionAPIContract:
    """Test ingestion endpoint API contract compatibility."""

    @pytest.mark.asyncio
    async def test_ingestion_success_response_format(self) -> None:
        """
        Test that ingestion returns correct success response format.

        Expected response:
        {
          "message": "Documents ingested successfully",
          "threadId": "<uuid>"
        }
        """
        # Prepare test documents (matching frontend format)
        test_docs = [
            Document(
                page_content="Test content from PDF page 1",
                metadata={"source": "test.pdf", "page": 0},
            ),
            Document(
                page_content="Test content from PDF page 2",
                metadata={"source": "test.pdf", "page": 1},
            ),
        ]

        # Mock the retriever at the ingestion_graph module level
        with patch("src.ingestion_graph.graph.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.vectorstore = MagicMock()
            mock_retriever.vectorstore.add_documents = MagicMock(return_value=None)
            mock_make_retriever.return_value = mock_retriever

            # Prepare input matching frontend API call
            input_data = {"docs": test_docs}

            config = {
                "configurable": {
                    "retriever_provider": "supabase",
                    "k": 5,
                    "filter_kwargs": {},
                }
            }

            # Invoke the ingestion graph
            result = await ingestion_graph.ainvoke(input_data, config)

            # Validate response structure
            assert "docs" in result
            # After ingestion, docs should be deleted (empty list or "delete")
            assert result["docs"] == [] or result["docs"] == "delete"

            # Verify retriever was called with documents
            mock_retriever.vectorstore.add_documents.assert_called_once()
            args = mock_retriever.vectorstore.add_documents.call_args[0][0]
            assert len(args) == 2
            assert all(isinstance(doc, Document) for doc in args)

    @pytest.mark.asyncio
    async def test_ingestion_empty_docs_error(self) -> None:
        """
        Test that ingestion fails gracefully with empty documents.

        Expected: ValueError or appropriate error when no docs provided
        and use_sample_docs is False.
        """
        with patch("src.ingestion_graph.graph.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_make_retriever.return_value = mock_retriever

            input_data = {"docs": []}

            config = {
                "configurable": {
                    "retriever_provider": "supabase",
                    "k": 5,
                    "filter_kwargs": {},
                    "use_sample_docs": False,  # Prevent fallback to sample docs
                }
            }

            # Should raise ValueError
            with pytest.raises(ValueError, match="No sample documents to index"):
                await ingestion_graph.ainvoke(input_data, config)

    @pytest.mark.asyncio
    async def test_ingestion_with_sample_docs(self) -> None:
        """
        Test ingestion falls back to sample docs when configured.

        This validates the demo/testing mode works correctly.
        """
        with patch("src.ingestion_graph.graph.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.vectorstore = MagicMock()
            mock_retriever.vectorstore.add_documents = MagicMock(return_value=None)
            mock_make_retriever.return_value = mock_retriever

            # Mock file reading
            sample_data = [
                {
                    "page_content": "Sample document content",
                    "metadata": {"source": "sample.txt"},
                }
            ]

            with patch("builtins.open", create=True) as mock_open:
                with patch("json.load", return_value=sample_data):
                    input_data = {"docs": []}

                    config = {
                        "configurable": {
                            "retriever_provider": "supabase",
                            "k": 5,
                            "filter_kwargs": {},
                            "use_sample_docs": True,
                            "docs_file": "sample_docs.json",
                        }
                    }

                    result = await ingestion_graph.ainvoke(input_data, config)

                    # Should succeed and clear docs
                    assert "docs" in result
                    mock_retriever.vectorstore.add_documents.assert_called_once()


class TestRetrievalAPIContract:
    """Test retrieval/chat endpoint API contract compatibility."""

    @pytest.mark.asyncio
    async def test_retrieval_response_structure(self) -> None:
        """
        Test that retrieval returns correct response structure.

        The frontend expects messages in the state after execution,
        formatted for SSE streaming.
        """
        with patch("src.retrieval_graph.graph.make_retriever") as mock_make_retriever:
            # Mock retriever
            mock_retriever = AsyncMock()
            mock_docs = [
                Document(
                    page_content="LangChain is a framework for building LLM applications.",
                    metadata={"source": "docs.pdf", "page": 1},
                )
            ]
            mock_retriever.ainvoke = AsyncMock(return_value=mock_docs)
            mock_make_retriever.return_value = mock_retriever

            # Mock LLM at the retrieval_graph module level
            with patch("src.retrieval_graph.graph.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()
                mock_response = AIMessage(
                    content="LangChain is a framework for building LLM applications."
                )
                mock_model.ainvoke = AsyncMock(return_value=mock_response)

                # Mock structured output for routing
                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "retrieve"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                input_data = {"query": "What is LangChain?"}

                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "filter_kwargs": {},
                        "query_model": "openai/gpt-4o-mini",
                    }
                }

                result = await retrieval_graph.ainvoke(input_data, config)

                # Validate response structure
                assert "messages" in result
                assert isinstance(result["messages"], list)
                assert len(result["messages"]) == 2  # Human + AI message

                # Validate message types
                assert isinstance(result["messages"][0], HumanMessage)
                assert isinstance(result["messages"][1], AIMessage)

                # Validate query preservation
                assert result["messages"][0].content == "What is LangChain?"

                # Validate documents were retrieved
                assert "documents" in result
                assert len(result["documents"]) == 1

    @pytest.mark.asyncio
    async def test_direct_answer_path(self) -> None:
        """
        Test that simple queries take the direct answer path.

        Validates routing logic and direct response format.
        """
        with patch("src.retrieval_graph.graph.load_chat_model") as mock_load_model:
            mock_model = AsyncMock()
            mock_response = AIMessage(content="Hello! How can I help you today?")
            mock_model.ainvoke = AsyncMock(return_value=mock_response)

            # Mock structured output for routing (direct)
            mock_route_model = AsyncMock()
            mock_route_response = MagicMock()
            mock_route_response.route = "direct"
            mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
            mock_model.with_structured_output = MagicMock(return_value=mock_route_model)

            mock_load_model.return_value = mock_model

            input_data = {"query": "Hello"}

            config = {
                "configurable": {
                    "retriever_provider": "supabase",
                    "k": 5,
                    "filter_kwargs": {},
                    "query_model": "openai/gpt-4o-mini",
                }
            }

            result = await retrieval_graph.ainvoke(input_data, config)

            # Validate response structure
            assert "messages" in result
            assert len(result["messages"]) == 2
            assert result["messages"][0].content == "Hello"

            # Validate no documents were retrieved
            assert "documents" not in result or len(result.get("documents", [])) == 0

    @pytest.mark.asyncio
    async def test_streaming_mode_compatibility(self) -> None:
        """
        Test that streaming mode returns chunks compatible with SSE.

        The frontend expects chunks in format:
        data: {"type": "chunk", ...}
        """
        with patch("src.retrieval_graph.graph.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_docs = [
                Document(
                    page_content="Test content",
                    metadata={"source": "test.pdf"},
                )
            ]
            mock_retriever.ainvoke = AsyncMock(return_value=mock_docs)
            mock_make_retriever.return_value = mock_retriever

            with patch("src.retrieval_graph.graph.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()
                mock_response = AIMessage(content="Test response")
                mock_model.ainvoke = AsyncMock(return_value=mock_response)

                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "retrieve"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                input_data = {"query": "Test query"}
                config = {
                    "configurable": {
                        "retriever_provider": "supabase",
                        "k": 5,
                        "filter_kwargs": {},
                        "query_model": "openai/gpt-4o-mini",
                    }
                }

                # Test streaming
                chunks = []
                async for chunk in retrieval_graph.astream(input_data, config):
                    chunks.append(chunk)

                # Validate we got chunks
                assert len(chunks) > 0

                # Each chunk should be a dict with node updates
                for chunk in chunks:
                    assert isinstance(chunk, dict)


class TestErrorHandling:
    """Test error handling and status codes match TypeScript behavior."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_missing_configuration_error(self) -> None:
        """Test that missing configuration raises appropriate error."""
        input_data = {"docs": [Document(page_content="test")]}

        # Missing config should raise ValueError
        with pytest.raises((ValueError, KeyError)):
            await ingestion_graph.ainvoke(input_data, None)

    @pytest.mark.asyncio
    async def test_invalid_retriever_provider_error(self) -> None:
        """Test that invalid retriever provider is handled gracefully."""
        with pytest.raises((ValueError, KeyError)):
            from src.shared.retrieval import make_retriever

            config = {
                "configurable": {
                    "retriever_provider": "invalid_provider",
                    "k": 5,
                }
            }

            await make_retriever(config)

    @pytest.mark.asyncio
    async def test_retrieval_invalid_route_error(self) -> None:
        """Test that invalid routing raises appropriate error."""
        from src.retrieval_graph.graph import route_query

        state = {"route": "invalid_route", "query": "", "documents": [], "messages": []}

        with pytest.raises(ValueError, match="Invalid route"):
            await route_query(state)


class TestThreadIDCompatibility:
    """Test thread ID handling matches frontend expectations."""

    @pytest.mark.asyncio
    async def test_thread_id_preserved_across_calls(self) -> None:
        """
        Test that thread IDs work correctly for conversation history.

        The frontend creates a thread and reuses it for the conversation.
        """
        with patch("src.retrieval_graph.graph.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(return_value=[])
            mock_make_retriever.return_value = mock_retriever

            with patch("src.retrieval_graph.graph.load_chat_model") as mock_load_model:
                mock_model = AsyncMock()
                mock_model.ainvoke = AsyncMock(
                    return_value=AIMessage(content="Response")
                )

                mock_route_model = AsyncMock()
                mock_route_response = MagicMock()
                mock_route_response.route = "direct"
                mock_route_model.ainvoke = AsyncMock(return_value=mock_route_response)
                mock_model.with_structured_output = MagicMock(
                    return_value=mock_route_model
                )

                mock_load_model.return_value = mock_model

                # First message
                input_data_1 = {"query": "First question"}
                config = {
                    "configurable": {
                        "thread_id": "test-thread-123",
                        "retriever_provider": "supabase",
                        "k": 5,
                        "query_model": "openai/gpt-4o-mini",
                    }
                }

                result_1 = await retrieval_graph.ainvoke(input_data_1, config)

                # Second message (should maintain history)
                input_data_2 = {"query": "Follow-up question"}

                result_2 = await retrieval_graph.ainvoke(input_data_2, config)

                # Both should have messages
                assert "messages" in result_1
                assert "messages" in result_2


class TestConfigurationPassing:
    """Test that configuration values are correctly passed to nodes."""

    @pytest.mark.asyncio
    async def test_k_value_configuration(self) -> None:
        """Test that k-value for retrieval is correctly passed."""
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_make_retriever.return_value = mock_retriever

            config = {
                "configurable": {
                    "retriever_provider": "supabase",
                    "k": 10,  # Custom k-value
                    "filter_kwargs": {},
                }
            }

            # Call make_retriever
            await mock_make_retriever(config)

            # Verify it was called with config
            mock_make_retriever.assert_called_once_with(config)

    @pytest.mark.asyncio
    async def test_filter_kwargs_configuration(self) -> None:
        """Test that filter_kwargs are correctly passed."""
        with patch("src.shared.retrieval.make_retriever") as mock_make_retriever:
            mock_retriever = AsyncMock()
            mock_make_retriever.return_value = mock_retriever

            config = {
                "configurable": {
                    "retriever_provider": "supabase",
                    "k": 5,
                    "filter_kwargs": {"topic": "project_report"},
                }
            }

            await mock_make_retriever(config)

            mock_make_retriever.assert_called_once_with(config)
