"""FastAPI application for AI PDF Chatbot backend.

This module provides a production-ready FastAPI layer that wraps the LangGraph
ingestion and retrieval graphs. It exposes HTTP endpoints for:
- Document ingestion (PDF processing)
- Chat with streaming responses
- Health checks and API documentation

The FastAPI layer preserves all LangGraph functionality while providing:
- Proper HTTP routing and error handling
- CORS support for frontend integration
- Request/response validation via Pydantic models
- OpenAPI documentation
"""

# Load environment variables FIRST before any other imports
# This ensures all modules that depend on env vars see them
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

import json
import logging
import os
import tempfile
import uuid
from typing import Any, AsyncGenerator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.ingestion_graph.graph import graph as ingestion_graph
from src.retrieval_graph.graph import graph as retrieval_graph

# Configure logger
logger = logging.getLogger(__name__)

# Constants
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Pydantic models for request/response validation


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., min_length=1, description="User message/query")
    thread_id: str = Field(..., alias="threadId", description="Conversation thread ID")
    config: dict | None = Field(
        default=None, description="Optional configuration for the retrieval graph"
    )


class IngestRequest(BaseModel):
    """Request model for document ingestion endpoint."""

    thread_id: str = Field(..., alias="threadId", description="Thread ID for ingestion")
    config: dict | None = Field(
        default=None, description="Optional configuration for the ingestion graph"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(default="healthy", description="Service health status")
    version: str = Field(default="0.1.0", description="API version")


# Initialize FastAPI app
app = FastAPI(
    title="AI PDF Chatbot API",
    description="Production API for LangGraph-based PDF chatbot with ingestion and retrieval",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware for Next.js frontend
# Get allowed origins from environment variable (comma-separated list)
# Defaults to localhost for development
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the service health status and version information.
    Useful for monitoring and load balancer health checks.

    Returns:
        HealthResponse: Service health status and version.
    """
    return HealthResponse(status="healthy", version="0.1.0")


@app.post("/api/ingest")
async def ingest_documents(
    file: UploadFile = File(...),
    thread_id: str = Form(..., alias="threadId"),
    config: str = Form(default="{}"),
) -> dict:
    """
    Ingest PDF documents into the vector store.

    This endpoint accepts PDF files, processes them through the ingestion graph,
    and stores the embeddings in Supabase vector store.

    Args:
        file: The PDF file to ingest (multipart/form-data).
        thread_id: Thread ID for tracking the ingestion process.
        config: JSON string containing configuration (optional).

    Returns:
        dict: Ingestion result with status and details.

    Raises:
        HTTPException: If file processing or ingestion fails.
    """
    temp_file_path = None
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Stream file content with size validation
        content = bytearray()
        chunk_size = 8192
        total_size = 0

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE / (1024 * 1024)}MB",
                )
            content.extend(chunk)

        # Parse config
        try:
            config_dict = json.loads(config)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid config JSON")

        # Use PyPDFLoader for proper PDF parsing
        # Write PDF bytes to temporary file (required by PyPDFLoader)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(content)
            temp_file_path = tmp_file.name

        # Load PDF using PyPDFLoader
        loader = PyPDFLoader(temp_file_path)
        documents = loader.load()

        # Add UUID to each document's metadata
        for doc in documents:
            if doc.metadata is None:
                doc.metadata = {}
            doc.metadata["uuid"] = str(uuid.uuid4())
            doc.metadata["source"] = file.filename

        # Build RunnableConfig with thread_id
        runnable_config = RunnableConfig(
            configurable={
                **config_dict.get("configurable", config_dict),
                "thread_id": thread_id,
            }
        )

        # Execute ingestion graph
        result = await ingestion_graph.ainvoke(
            {"docs": documents}, config=runnable_config, stream_mode=["updates"]  # type: ignore[arg-type]
        )

        return {
            "status": "success",
            "message": f"Successfully ingested {file.filename} ({len(documents)} pages)",
            "thread_id": thread_id,
            "pages": len(documents),
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log the full error with stack trace for debugging
        logger.error(f"Ingestion failed for {file.filename}: {str(e)}", exc_info=True)
        # Return detailed error message for debugging (sanitize in production)
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass  # Log in production, but don't fail the request


async def stream_chat_response(
    message: str, thread_id: str, config: dict | None
) -> AsyncGenerator[str, None]:
    """
    Stream chat responses from the retrieval graph.

    This async generator yields Server-Sent Events (SSE) formatted chunks
    from the LangGraph retrieval graph execution.

    Args:
        message: User message/query.
        thread_id: Conversation thread ID for conversation history.
        config: Optional configuration dict.

    Yields:
        str: SSE-formatted event strings (data: {json}\n\n).
    """
    try:
        # Build RunnableConfig with thread_id for conversation memory
        config_dict = config if config else {}
        runnable_config = RunnableConfig(
            configurable={
                **config_dict.get("configurable", config_dict),
                "thread_id": thread_id,
            }
        )

        # Stream from retrieval graph
        async for chunk in retrieval_graph.astream(
            {"query": message, "messages": [], "route": "", "documents": []},  # type: ignore[arg-type]
            config=runnable_config,
            stream_mode=["messages", "updates"],
        ):
            # Format chunk as SSE event
            event_data = format_stream_chunk(chunk)  # type: ignore[arg-type]
            if event_data:
                yield f"data: {json.dumps(event_data)}\n\n"

    except Exception as e:
        # Log the full error with stack trace
        logger.error(f"Stream error for thread {thread_id}: {str(e)}", exc_info=True)
        # Use "event" key to match LangGraph SDK format
        error_event = {"event": "error", "data": {"message": "Chat processing failed"}}
        yield f"data: {json.dumps(error_event)}\n\n"


def format_stream_chunk(chunk: tuple) -> dict | None:
    """
    Format a LangGraph stream chunk for SSE transmission in LangGraph SDK format.

    Converts LangGraph stream chunks (which are tuples of node name and data)
    into the format expected by the frontend (matching LangGraph SDK format).

    Frontend expects:
    - For message chunks: {"event": "messages/partial", "data": [{"type": "ai", "content": "..."}]}
    - For state updates: {"event": "updates", "data": {"nodeName": {...}}}

    Args:
        chunk: LangGraph stream chunk (node_name, data) tuple.

    Returns:
        dict: Formatted chunk data or None if not serializable.
    """
    try:
        # chunk is typically a tuple: (node_name, data)
        if isinstance(chunk, tuple) and len(chunk) == 2:
            node_name, data = chunk

            # Handle different data types
            if isinstance(data, BaseMessage):
                # For message chunks - format as messages/partial event with array
                return {
                    "event": "messages/partial",
                    "data": [
                        {
                            "type": data.type,
                            "content": data.content,
                            "id": getattr(data, "id", None),
                        }
                    ],
                }
            elif isinstance(data, dict):
                # For state updates - format as updates event with nested data by node name
                return {
                    "event": "updates",
                    "data": {node_name: serialize_state_data(data)},
                }

        return None
    except Exception as e:
        logger.error(f"Error formatting stream chunk: {str(e)}", exc_info=True)
        return None


def serialize_state_data(data: dict) -> dict:
    """
    Serialize state data for JSON transmission.

    Converts complex objects (Documents, Messages) to JSON-serializable dicts.

    Args:
        data: State data dict potentially containing complex objects.

    Returns:
        dict: Serialized data safe for JSON encoding.
    """
    serialized = {}
    for key, value in data.items():
        if isinstance(value, list):
            serialized[key] = [serialize_item(item) for item in value]
        else:
            serialized[key] = serialize_item(value)
    return serialized


def serialize_item(item: Any) -> Any:
    """
    Serialize a single item for JSON transmission.

    Args:
        item: Item to serialize (Document, Message, or primitive).

    Returns:
        Serialized item safe for JSON encoding.
    """
    if isinstance(item, Document):
        return {
            "page_content": item.page_content,
            "metadata": item.metadata,
        }
    elif isinstance(item, BaseMessage):
        return {
            "content": item.content,
            "type": item.type,
            "id": getattr(item, "id", None),
        }
    elif isinstance(item, dict):
        # Recursively serialize dict values
        return {k: serialize_item(v) for k, v in item.items()}
    elif isinstance(item, (list, tuple)):
        # Recursively serialize list/tuple items
        return [serialize_item(i) for i in item]
    elif hasattr(item, "dict"):
        # Pydantic models
        return item.dict()
    elif hasattr(item, "__dict__"):
        # Other objects with __dict__
        return item.__dict__
    else:
        # Primitives (str, int, float, bool, None)
        return item


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """
    Chat endpoint with streaming responses.

    This endpoint accepts user messages and streams responses from the
    retrieval graph using Server-Sent Events (SSE).

    Args:
        request: ChatRequest containing message, thread_id, and optional config.

    Returns:
        StreamingResponse: SSE stream of chat responses.

    Raises:
        HTTPException: If chat processing fails.
    """
    try:
        return StreamingResponse(
            stream_chat_response(request.message, request.thread_id, request.config),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# For local development with uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
