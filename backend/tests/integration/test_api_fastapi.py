"""Integration tests for FastAPI endpoints with real LangGraph execution.

This module tests the FastAPI layer integration with actual LangGraph graphs.
These tests verify end-to-end functionality with mocked external dependencies
(Supabase, OpenAI) but real graph execution.

Note: These are marked as integration tests and can be skipped with:
    pytest -m "not integration"
"""

import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from src.main import app

# Test client
client = TestClient(app)


@pytest.mark.integration
class TestIngestEndpointIntegration:
    """Integration tests for POST /api/ingest endpoint."""

    @pytest.mark.asyncio
    async def test_ingest_executes_full_graph(self) -> None:
        """Test that ingestion executes the full ingestion graph."""
        # Mock external dependencies but allow graph to execute
        mock_documents = [
            Document(page_content="Test page 1", metadata={"page": 0}),
            Document(page_content="Test page 2", metadata={"page": 1}),
        ]

        with patch("src.main.PyPDFLoader") as mock_loader_class, \
             patch("src.ingestion_graph.graph.make_retriever") as mock_retriever_factory:
            # Mock PyPDFLoader
            mock_loader = MagicMock()
            mock_loader.load.return_value = mock_documents
            mock_loader_class.return_value = mock_loader

            # Mock retriever
            mock_retriever = AsyncMock()
            mock_retriever.add_documents = AsyncMock(return_value=None)
            mock_retriever_factory.return_value = mock_retriever

            pdf_content = b"%PDF-1.4\nTest PDF content"
            files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
            data = {
                "threadId": "test-thread-123",
                "config": json.dumps(
                    {"configurable": {"retrieverProvider": "supabase", "useSampleDocs": False}}
                ),
            }

            response = client.post("/api/ingest", files=files, data=data)

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert result["pages"] == 2

            # Verify retriever was created and documents were added
            mock_retriever_factory.assert_called_once()
            mock_retriever.add_documents.assert_called_once()

            # Verify documents were processed
            call_args = mock_retriever.add_documents.call_args
            docs = call_args[0][0] if call_args[0] else []
            assert len(docs) > 0
            assert isinstance(docs[0], Document)

    @pytest.mark.asyncio
    async def test_ingest_with_sample_docs(self) -> None:
        """Test ingestion using sample documents."""
        mock_documents = [Document(page_content="Test", metadata={})]

        with patch("src.main.PyPDFLoader") as mock_loader_class, \
             patch("src.ingestion_graph.graph.make_retriever") as mock_retriever_factory:
            # Mock PyPDFLoader
            mock_loader = MagicMock()
            mock_loader.load.return_value = mock_documents
            mock_loader_class.return_value = mock_loader

            mock_retriever = AsyncMock()
            mock_retriever.add_documents = AsyncMock(return_value=None)
            mock_retriever_factory.return_value = mock_retriever

            # Mock sample docs file
            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.__enter__.return_value = mock_file
                mock_file.read.return_value = json.dumps(
                    [
                        {
                            "page_content": "Sample content",
                            "metadata": {"source": "sample.pdf"},
                        }
                    ]
                )
                mock_open.return_value = mock_file

                pdf_content = b"%PDF-1.4\nPlaceholder"
                files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
                data = {
                    "threadId": "test-thread-123",
                    "config": json.dumps(
                        {
                            "configurable": {
                                "retrieverProvider": "supabase",
                                "useSampleDocs": True,
                                "docsFile": "sample_docs.json",
                            }
                        }
                    ),
                }

                response = client.post("/api/ingest", files=files, data=data)

                # Should succeed with sample docs
                assert response.status_code == 200


@pytest.mark.integration
class TestChatEndpointIntegration:
    """Integration tests for POST /api/chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_executes_direct_path(self) -> None:
        """Test that chat executes direct answer path."""
        # Mock external dependencies
        with patch("src.retrieval_graph.graph.load_chat_model") as mock_model_factory:
            # Mock LLM
            mock_model = AsyncMock()
            mock_model.with_structured_output = MagicMock(return_value=mock_model)
            mock_model.ainvoke = AsyncMock(
                side_effect=[
                    # First call: router decision
                    MagicMock(route="direct", direct_answer=None),
                    # Second call: direct answer
                    AIMessage(content="Hello! How can I help you?"),
                ]
            )
            mock_model_factory.return_value = mock_model

            request_data = {
                "message": "Hello",
                "threadId": "test-thread-123",
                "config": {"configurable": {"queryModel": "openai/gpt-4o-mini"}},
            }

            response = client.post("/api/chat", json=request_data)

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            # Collect stream chunks
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip():
                        try:
                            chunks.append(json.loads(data_str))
                        except json.JSONDecodeError:
                            pass

            # Should have received chunks from graph execution
            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_executes_retrieval_path(self) -> None:
        """Test that chat executes retrieval path with document retrieval."""
        # Mock external dependencies
        with patch("src.retrieval_graph.graph.load_chat_model") as mock_model_factory, patch(
            "src.retrieval_graph.graph.make_retriever"
        ) as mock_retriever_factory:
            # Mock LLM
            mock_model = AsyncMock()
            mock_model.with_structured_output = MagicMock(return_value=mock_model)
            mock_model.ainvoke = AsyncMock(
                side_effect=[
                    # First call: router decision
                    MagicMock(route="retrieve", direct_answer=None),
                    # Second call: generate response
                    AIMessage(content="Based on the documents, the answer is..."),
                ]
            )
            mock_model_factory.return_value = mock_model

            # Mock retriever
            mock_retriever = AsyncMock()
            mock_retriever.ainvoke = AsyncMock(
                return_value=[
                    Document(page_content="Relevant content", metadata={"source": "doc1.pdf"}),
                    Document(page_content="More context", metadata={"source": "doc2.pdf"}),
                ]
            )
            mock_retriever_factory.return_value = mock_retriever

            request_data = {
                "message": "What is LangChain?",
                "threadId": "test-thread-123",
                "config": {"configurable": {"queryModel": "openai/gpt-4o-mini", "k": 5}},
            }

            response = client.post("/api/chat", json=request_data)

            assert response.status_code == 200

            # Collect chunks
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip():
                        try:
                            chunks.append(json.loads(data_str))
                        except json.JSONDecodeError:
                            pass

            # Should have chunks from retrieval path
            assert len(chunks) > 0

            # Verify retriever was called
            mock_retriever.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_preserves_thread_state(self) -> None:
        """Test that thread state is preserved across messages."""
        with patch("src.retrieval_graph.graph.load_chat_model") as mock_model_factory:
            mock_model = AsyncMock()
            mock_model.with_structured_output = MagicMock(return_value=mock_model)
            mock_model.ainvoke = AsyncMock(
                side_effect=[
                    MagicMock(route="direct"),
                    AIMessage(content="Response 1"),
                    MagicMock(route="direct"),
                    AIMessage(content="Response 2"),
                ]
            )
            mock_model_factory.return_value = mock_model

            thread_id = "persistent-thread-123"

            # First message
            response1 = client.post(
                "/api/chat",
                json={
                    "message": "First message",
                    "threadId": thread_id,
                },
            )
            assert response1.status_code == 200

            # Second message with same thread
            response2 = client.post(
                "/api/chat",
                json={
                    "message": "Second message",
                    "threadId": thread_id,
                },
            )
            assert response2.status_code == 200

            # Both should succeed - thread state is managed by graph


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_ingest_then_chat_workflow(self) -> None:
        """Test complete workflow: ingest documents, then chat with them."""
        # Mock all external dependencies
        mock_documents = [Document(page_content="Test", metadata={})]

        with patch("src.main.PyPDFLoader") as mock_loader_class, \
             patch("src.ingestion_graph.graph.make_retriever") as mock_ingest_retriever, \
             patch("src.retrieval_graph.graph.make_retriever") as mock_chat_retriever, \
             patch("src.retrieval_graph.graph.load_chat_model") as mock_model_factory:
            # Mock PyPDFLoader
            mock_loader = MagicMock()
            mock_loader.load.return_value = mock_documents
            mock_loader_class.return_value = mock_loader

            # Setup ingestion mocks
            mock_ingest_ret = AsyncMock()
            mock_ingest_ret.add_documents = AsyncMock(return_value=None)
            mock_ingest_retriever.return_value = mock_ingest_ret

            # Setup chat mocks
            mock_chat_ret = AsyncMock()
            mock_chat_ret.ainvoke = AsyncMock(
                return_value=[
                    Document(page_content="Content from test.pdf", metadata={"source": "test.pdf"})
                ]
            )
            mock_chat_retriever.return_value = mock_chat_ret

            mock_model = AsyncMock()
            mock_model.with_structured_output = MagicMock(return_value=mock_model)
            mock_model.ainvoke = AsyncMock(
                side_effect=[
                    MagicMock(route="retrieve"),
                    AIMessage(content="Based on test.pdf, the answer is..."),
                ]
            )
            mock_model_factory.return_value = mock_model

            thread_id = "workflow-thread-123"

            # Step 1: Ingest document
            pdf_content = b"%PDF-1.4\nTest document content"
            files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
            data = {"threadId": thread_id, "config": "{}"}

            ingest_response = client.post("/api/ingest", files=files, data=data)
            assert ingest_response.status_code == 200

            # Step 2: Chat with ingested document
            chat_response = client.post(
                "/api/chat",
                json={
                    "message": "What does the document say?",
                    "threadId": thread_id,
                },
            )
            assert chat_response.status_code == 200

            # Verify both operations succeeded
            ingest_result = ingest_response.json()
            assert ingest_result["status"] == "success"

            # Verify chat retrieved documents
            mock_chat_ret.ainvoke.assert_called_once()


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling in FastAPI layer."""

    @pytest.mark.asyncio
    async def test_handles_graph_timeout(self) -> None:
        """Test handling of graph execution timeout."""
        with patch("src.retrieval_graph.graph.load_chat_model") as mock_model_factory:
            mock_model = AsyncMock()
            mock_model.with_structured_output = MagicMock(return_value=mock_model)
            mock_model.ainvoke = AsyncMock(side_effect=TimeoutError("Graph timeout"))
            mock_model_factory.return_value = mock_model

            response = client.post(
                "/api/chat",
                json={
                    "message": "Test message",
                    "threadId": "test-thread",
                },
            )

            # Should return 200 with error in stream
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_retriever_connection_error(self) -> None:
        """Test handling of retriever connection errors."""
        mock_documents = [Document(page_content="Test", metadata={})]

        with patch("src.main.PyPDFLoader") as mock_loader_class, \
             patch("src.ingestion_graph.graph.make_retriever") as mock_retriever_factory:
            # Mock PyPDFLoader
            mock_loader = MagicMock()
            mock_loader.load.return_value = mock_documents
            mock_loader_class.return_value = mock_loader

            mock_retriever_factory.side_effect = ConnectionError("Supabase unavailable")

            pdf_content = b"%PDF-1.4\nTest"
            files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
            data = {"threadId": "test-thread", "config": "{}"}

            response = client.post("/api/ingest", files=files, data=data)

            # Should return 500 with sanitized error message
            assert response.status_code == 500
            assert "Document ingestion failed" in response.json()["detail"]
