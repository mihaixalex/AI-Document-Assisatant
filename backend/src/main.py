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

from src.conversations.repository import get_repository
from src.conversations.routes import router as conversations_router
from src.ingestion_graph import graph as ingestion_graph_module
from src.retrieval_graph import graph as retrieval_graph_module

# Import the initial graphs (will be replaced with checkpointer versions on startup)
ingestion_graph = ingestion_graph_module.graph
retrieval_graph = retrieval_graph_module.graph

# Configure logger
logger = logging.getLogger(__name__)

# Constants
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Pydantic models for request/response validation


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., min_length=1, description="User message/query")
    thread_id: str = Field(
        ...,
        alias="threadId",
        min_length=1,
        max_length=128,
        description="Conversation thread ID"
    )
    config: dict | None = Field(
        default=None, description="Optional configuration for the retrieval graph"
    )


class IngestRequest(BaseModel):
    """Request model for document ingestion endpoint."""

    thread_id: str = Field(
        ...,
        alias="threadId",
        min_length=1,
        max_length=128,
        description="Thread ID for ingestion"
    )
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

# Register conversation management routes
app.include_router(conversations_router)


@app.on_event("startup")
async def startup_event() -> None:
    """
    FastAPI startup event handler.

    Initializes the PostgresSaver checkpointer and recompiles both graphs
    with persistence enabled. This ensures conversation history is maintained
    across requests.

    If DATABASE_URL is not set or checkpointer initialization fails,
    the graphs will continue to work without persistence.
    """
    global ingestion_graph, retrieval_graph

    try:
        logger.info("Initializing PostgresSaver checkpointer for graphs...")

        # Recompile both graphs with checkpointer
        ingestion_graph = await ingestion_graph_module.compile_with_checkpointer()
        retrieval_graph = await retrieval_graph_module.compile_with_checkpointer()

        logger.info("Successfully initialized checkpointer for both graphs")
    except Exception as e:
        logger.warning(
            f"Failed to initialize checkpointer, graphs will run without persistence: {e}"
        )
        # Graphs will continue to use the default compiled versions without checkpointer


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    FastAPI shutdown event handler.

    Cleanup resources on application shutdown:
    - Close the checkpointer connection pool
    - Close the conversation repository connection pool
    """
    # Close checkpointer connection pool
    try:
        from src.shared.checkpointer import cleanup_checkpointer

        await cleanup_checkpointer()
        logger.info("Successfully closed checkpointer connection pool")
    except Exception as e:
        logger.warning("Failed to close checkpointer pool: %s", e)

    # Close conversation repository connection pool
    try:
        from src.conversations.repository import get_repository

        repository = get_repository()
        await repository.close()
        logger.info("Successfully closed conversation repository connection pool")
    except Exception as e:
        logger.warning("Failed to close conversation repository pool: %s", e)


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
    thread_id: str = Form(..., alias="threadId", min_length=1, max_length=128),
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

        # Validate thread_id is not empty
        if not thread_id or thread_id.strip() == "":
            raise HTTPException(status_code=400, detail="threadId cannot be empty")

        # Use PyPDFLoader for proper PDF parsing
        # Write PDF bytes to temporary file (required by PyPDFLoader)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(content)
            temp_file_path = tmp_file.name

        # Load PDF using PyPDFLoader
        loader = PyPDFLoader(temp_file_path)
        documents = loader.load()

        # Extract is_shared flag from config (defaults to False) - strict boolean validation
        is_shared_value = config_dict.get("configurable", {}).get("is_shared", False)
        is_shared = is_shared_value is True  # Strict boolean check

        # Fetch conversation title for metadata labeling (if not shared)
        conversation_title = None
        if not is_shared:
            try:
                repo = get_repository()
                conversation = await repo.get_conversation(thread_id)
                if conversation:
                    conversation_title = conversation.get("title")
            except Exception as e:
                logger.warning(f"Could not fetch conversation title: {e}")

        # Add UUID and thread_id to each document's metadata
        for doc in documents:
            if doc.metadata is None:
                doc.metadata = {}
            doc.metadata["uuid"] = str(uuid.uuid4())
            doc.metadata["source"] = file.filename
            # Set thread_id based on shared flag - "__SHARED__" for shared docs
            if is_shared:
                doc.metadata["thread_id"] = "__SHARED__"
                doc.metadata["visibility"] = "shared"
                doc.metadata["conversation_title"] = None
            else:
                doc.metadata["thread_id"] = thread_id
                doc.metadata["visibility"] = "private"
                doc.metadata["conversation_title"] = conversation_title

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

        logger.info(f"Starting stream for thread {thread_id} with message: {message[:50]}...")

        # Stream from retrieval graph - use only 'updates' mode for reliability
        # The 'updates' mode yields state updates after each node completes
        async for chunk in retrieval_graph.astream(
            {"query": message, "messages": [], "route": "", "documents": []},  # type: ignore[arg-type]
            config=runnable_config,
            stream_mode="updates",
        ):
            # With stream_mode="updates", chunk is a dict: {node_name: state_update}
            if isinstance(chunk, dict):
                for node_name, state_data in chunk.items():
                    event_data = {
                        "event": "updates",
                        "data": {node_name: serialize_state_data(state_data) if isinstance(state_data, dict) else state_data},
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

        # Send completion event
        logger.info(f"Stream completed for thread {thread_id}")
        yield f"data: {json.dumps({'event': 'done', 'data': {}})}\n\n"

    except Exception as e:
        # Log the full error with stack trace
        logger.error(f"Stream error for thread {thread_id}: {str(e)}", exc_info=True)
        # Use "event" key to match LangGraph SDK format
        error_event = {"event": "error", "data": {"message": str(e)}}
        yield f"data: {json.dumps(error_event)}\n\n"


def format_stream_chunk(chunk: tuple) -> dict | None:
    """
    Format a LangGraph stream chunk for SSE transmission in LangGraph SDK format.

    Converts LangGraph stream chunks into the format expected by the frontend.

    When using multiple stream_mode (e.g., ["messages", "updates"]), chunks are
    nested tuples: (stream_mode, (node_name, data))

    When using single stream_mode, chunks are: (node_name, data)

    Frontend expects:
    - For message chunks: {"event": "messages/partial", "data": [{"type": "ai", "content": "..."}]}
    - For state updates: {"event": "updates", "data": {"nodeName": {...}}}

    Args:
        chunk: LangGraph stream chunk - either (stream_mode, (node_name, data))
               or (node_name, data) tuple.

    Returns:
        dict: Formatted chunk data or None if not serializable.
    """
    try:
        if not isinstance(chunk, tuple) or len(chunk) != 2:
            return None

        first, second = chunk

        # Check if this is a nested tuple from multiple stream modes
        # Pattern: (stream_mode_str, (node_name, data))
        if isinstance(first, str) and isinstance(second, tuple) and len(second) == 2:
            stream_mode = first
            node_name, data = second

            if stream_mode == "messages":
                # Message stream mode - data is a BaseMessage
                if isinstance(data, BaseMessage):
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
            elif stream_mode == "updates":
                # Updates stream mode - data is a state dict
                if isinstance(data, dict):
                    return {
                        "event": "updates",
                        "data": {node_name: serialize_state_data(data)},
                    }
        else:
            # Fallback for single stream_mode: (node_name, data)
            node_name, data = first, second

            if isinstance(data, BaseMessage):
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
    # Validate thread_id is not empty or whitespace-only
    if not request.thread_id or request.thread_id.strip() == "":
        raise HTTPException(status_code=400, detail="threadId cannot be empty")

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
