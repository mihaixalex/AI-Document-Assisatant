"""Unit tests for FastAPI endpoints in src/main.py.

This module tests all FastAPI endpoints with mocked LangGraph execution:
- GET /health
- POST /api/ingest
- POST /api/chat (streaming)
"""

import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from src.main import app

# Test client
client = TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_check_returns_200(self) -> None:
        """Test that health check returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_correct_structure(self) -> None:
        """Test that health check returns expected JSON structure."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


class TestIngestEndpoint:
    """Tests for POST /api/ingest endpoint."""

    @pytest.mark.asyncio
    async def test_ingest_success_with_pdf(self) -> None:
        """Test successful PDF ingestion."""
        # Mock PyPDFLoader and ingestion graph
        mock_documents = [
            Document(page_content="Test page 1", metadata={"page": 0}),
            Document(page_content="Test page 2", metadata={"page": 1}),
        ]

        with patch("src.main.PyPDFLoader") as mock_loader_class, \
             patch("src.main.ingestion_graph") as mock_graph:
            # Setup mocks
            mock_loader = MagicMock()
            mock_loader.load.return_value = mock_documents
            mock_loader_class.return_value = mock_loader
            mock_graph.ainvoke = AsyncMock(return_value={"docs": "delete"})

            # Create a test PDF file
            pdf_content = b"%PDF-1.4\nTest PDF content"
            files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
            data = {"threadId": "test-thread-123", "config": "{}"}

            response = client.post("/api/ingest", files=files, data=data)

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert result["thread_id"] == "test-thread-123"
            assert "test.pdf" in result["message"]
            assert result["pages"] == 2

            # Verify graph was called
            mock_graph.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_rejects_non_pdf_files(self) -> None:
        """Test that non-PDF files are rejected."""
        txt_content = b"This is a text file"
        files = {"file": ("test.txt", BytesIO(txt_content), "text/plain")}
        data = {"threadId": "test-thread-123", "config": "{}"}

        response = client.post("/api/ingest", files=files, data=data)

        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_ingest_handles_invalid_config_json(self) -> None:
        """Test that invalid config JSON returns 400."""
        pdf_content = b"%PDF-1.4\nTest PDF"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        data = {"threadId": "test-thread-123", "config": "invalid json{"}

        response = client.post("/api/ingest", files=files, data=data)

        assert response.status_code == 400
        assert "config" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_ingest_handles_graph_errors(self) -> None:
        """Test that graph execution errors are handled properly."""
        mock_documents = [Document(page_content="Test", metadata={})]

        with patch("src.main.PyPDFLoader") as mock_loader_class, \
             patch("src.main.ingestion_graph") as mock_graph:
            mock_loader = MagicMock()
            mock_loader.load.return_value = mock_documents
            mock_loader_class.return_value = mock_loader
            mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph error"))

            pdf_content = b"%PDF-1.4\nTest PDF"
            files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
            data = {"threadId": "test-thread-123", "config": "{}"}

            response = client.post("/api/ingest", files=files, data=data)

            assert response.status_code == 500
            assert "Document ingestion failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_ingest_with_custom_config(self) -> None:
        """Test ingestion with custom configuration."""
        mock_documents = [Document(page_content="Test", metadata={})]

        with patch("src.main.PyPDFLoader") as mock_loader_class, \
             patch("src.main.ingestion_graph") as mock_graph:
            mock_loader = MagicMock()
            mock_loader.load.return_value = mock_documents
            mock_loader_class.return_value = mock_loader
            mock_graph.ainvoke = AsyncMock(return_value={"docs": "delete"})

            pdf_content = b"%PDF-1.4\nTest PDF"
            files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
            config = {"configurable": {"retrieverProvider": "supabase", "k": 10}}
            data = {"threadId": "test-thread-123", "config": json.dumps(config)}

            response = client.post("/api/ingest", files=files, data=data)

            assert response.status_code == 200

            # Verify config was passed to graph with thread_id
            call_args = mock_graph.ainvoke.call_args
            assert call_args is not None
            assert "config" in call_args.kwargs
            config_arg = call_args.kwargs["config"]
            assert config_arg.get("configurable")["retrieverProvider"] == "supabase"
            assert config_arg.get("configurable")["k"] == 10
            assert config_arg.get("configurable")["thread_id"] == "test-thread-123"


class TestChatEndpoint:
    """Tests for POST /api/chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_returns_streaming_response(self) -> None:
        """Test that chat endpoint returns streaming response."""
        # Mock the retrieval graph
        async def mock_astream(*args, **kwargs):
            """Mock async stream that yields test chunks."""
            yield ("checkQueryType", {"route": "direct"})
            yield ("directAnswer", {"messages": [AIMessage(content="Hello!")]})

        with patch("src.main.retrieval_graph") as mock_graph:
            mock_graph.astream = mock_astream

            request_data = {
                "message": "Hello",
                "threadId": "test-thread-123",
                "config": None,
            }

            response = client.post("/api/chat", json=request_data)

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    @pytest.mark.asyncio
    async def test_chat_streams_multiple_chunks(self) -> None:
        """Test that multiple chunks are streamed correctly."""

        async def mock_astream(*args, **kwargs):
            """Mock stream with multiple chunks."""
            yield ("checkQueryType", {"route": "retrieve"})
            yield (
                "retrieveDocuments",
                {"documents": [Document(page_content="Test doc", metadata={})]},
            )
            yield (
                "generateResponse",
                {"messages": [HumanMessage(content="Query"), AIMessage(content="Answer")]},
            )

        with patch("src.main.retrieval_graph") as mock_graph:
            mock_graph.astream = mock_astream

            request_data = {
                "message": "What is LangChain?",
                "threadId": "test-thread-123",
            }

            response = client.post("/api/chat", json=request_data)

            # Read streaming response
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str.strip():
                        chunks.append(json.loads(data_str))

            # Should have received multiple chunks
            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_handles_stream_errors(self) -> None:
        """Test that streaming errors are handled gracefully."""

        async def mock_astream_with_error(*args, **kwargs):
            """Mock stream that raises an error."""
            yield ("checkQueryType", {"route": "direct"})
            raise Exception("Stream error occurred")

        with patch("src.main.retrieval_graph") as mock_graph:
            mock_graph.astream = mock_astream_with_error

            request_data = {
                "message": "Hello",
                "threadId": "test-thread-123",
            }

            response = client.post("/api/chat", json=request_data)

            # Should still return 200 with error in stream
            assert response.status_code == 200

            # Check for error event in stream
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip():
                        chunks.append(json.loads(data_str))

            # Should have at least one chunk before error
            assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_chat_with_custom_config(self) -> None:
        """Test chat with custom configuration."""

        async def mock_astream(*args, **kwargs):
            """Mock stream that checks config."""
            # Verify config was passed
            assert "config" in kwargs
            yield ("directAnswer", {"messages": [AIMessage(content="Response")]})

        with patch("src.main.retrieval_graph") as mock_graph:
            mock_graph.astream = mock_astream

            config = {"configurable": {"queryModel": "gpt-4o", "k": 10}}
            request_data = {
                "message": "Hello",
                "threadId": "test-thread-123",
                "config": config,
            }

            response = client.post("/api/chat", json=request_data)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_validates_required_fields(self) -> None:
        """Test that required fields are validated."""
        # Missing message
        response = client.post("/api/chat", json={"threadId": "test-123"})
        assert response.status_code == 422

        # Missing threadId
        response = client.post("/api/chat", json={"message": "Hello"})
        assert response.status_code == 422

        # Empty message
        response = client.post("/api/chat", json={"message": "", "threadId": "test-123"})
        assert response.status_code == 422


class TestSerializationHelpers:
    """Tests for serialization helper functions."""

    def test_serialize_document(self) -> None:
        """Test Document serialization."""
        from src.main import serialize_item

        doc = Document(page_content="Test content", metadata={"source": "test.pdf"})
        result = serialize_item(doc)

        assert isinstance(result, dict)
        assert result["page_content"] == "Test content"
        assert result["metadata"]["source"] == "test.pdf"

    def test_serialize_message(self) -> None:
        """Test BaseMessage serialization."""
        from src.main import serialize_item

        msg = AIMessage(content="Hello", id="msg-123")
        result = serialize_item(msg)

        assert isinstance(result, dict)
        assert result["content"] == "Hello"
        assert result["type"] == "ai"
        assert result["id"] == "msg-123"

    def test_serialize_primitives(self) -> None:
        """Test primitive type serialization."""
        from src.main import serialize_item

        assert serialize_item("string") == "string"
        assert serialize_item(123) == 123
        assert serialize_item(True) is True
        assert serialize_item(None) is None

    def test_serialize_state_data(self) -> None:
        """Test state data dict serialization."""
        from src.main import serialize_state_data

        state_data = {
            "route": "retrieve",
            "documents": [Document(page_content="Test", metadata={})],
            "messages": [AIMessage(content="Answer")],
        }

        result = serialize_state_data(state_data)

        assert isinstance(result, dict)
        assert result["route"] == "retrieve"
        assert isinstance(result["documents"], list)
        assert isinstance(result["messages"], list)

    def test_format_stream_chunk_with_dict(self) -> None:
        """Test formatting stream chunk with dict data (state updates)."""
        from src.main import format_stream_chunk

        chunk = ("checkQueryType", {"route": "direct"})
        result = format_stream_chunk(chunk)

        assert result is not None
        assert result["event"] == "updates"
        assert "checkQueryType" in result["data"]
        assert result["data"]["checkQueryType"]["route"] == "direct"

    def test_format_stream_chunk_with_message(self) -> None:
        """Test formatting stream chunk with message data (LangGraph SDK format)."""
        from src.main import format_stream_chunk

        msg = AIMessage(content="Hello", id="msg-123")
        chunk = ("directAnswer", msg)
        result = format_stream_chunk(chunk)

        assert result is not None
        assert result["event"] == "messages/partial"
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1
        assert result["data"][0]["content"] == "Hello"
        assert result["data"][0]["type"] == "ai"
        assert result["data"][0]["id"] == "msg-123"

    def test_format_stream_chunk_handles_invalid_input(self) -> None:
        """Test that invalid chunks return None."""
        from src.main import format_stream_chunk

        assert format_stream_chunk(None) is None
        assert format_stream_chunk("not a tuple") is None
        assert format_stream_chunk((1,)) is None  # Wrong tuple length


class TestCORSConfiguration:
    """Tests for CORS middleware configuration."""

    def test_cors_allows_localhost(self) -> None:
        """Test that CORS allows requests from localhost:3000."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.status_code == 200
        # Note: TestClient doesn't fully simulate CORS, but we can verify endpoint works

    def test_options_request_handled(self) -> None:
        """Test that OPTIONS requests are handled for CORS preflight."""
        response = client.options(
            "/api/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # OPTIONS should be handled by CORS middleware
        assert response.status_code in [200, 204]


class TestAPIDocumentation:
    """Tests for OpenAPI documentation endpoints."""

    def test_docs_endpoint_accessible(self) -> None:
        """Test that /docs endpoint is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_available(self) -> None:
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "AI PDF Chatbot API"

    def test_redoc_endpoint_accessible(self) -> None:
        """Test that /redoc endpoint is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
