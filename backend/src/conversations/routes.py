"""FastAPI routes for conversation management.

This module defines REST API endpoints for:
- Listing conversations with pagination
- Creating new conversations with server-generated thread_id
- Loading conversation history from LangGraph checkpointer
- Updating conversation metadata (title)
- Soft deleting conversations
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from langchain_core.runnables import RunnableConfig

from src.conversations.models import (
    ConversationCreate,
    ConversationHistoryResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    DeleteResponse,
)
from src.conversations.repository import ConversationRepository, get_repository

logger = logging.getLogger(__name__)

# Create router for conversation endpoints
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    limit: Annotated[int, Query(ge=1, le=100, description="Page size limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    repository: ConversationRepository = Depends(get_repository),
) -> ConversationListResponse:
    """List all non-deleted conversations ordered by updated_at DESC.

    This endpoint supports pagination and is optimized for <500ms response time.

    Args:
        limit: Maximum number of conversations to return (1-100, default 50)
        offset: Number of conversations to skip (default 0)
        repository: Injected conversation repository

    Returns:
        ConversationListResponse with conversations list and pagination metadata
    """
    try:
        conversations, total = await repository.list_conversations(limit=limit, offset=offset)

        # Convert dict results to ConversationResponse models
        conversation_models = [ConversationResponse(**conv) for conv in conversations]

        return ConversationListResponse(
            conversations=conversation_models, total=total, limit=limit, offset=offset
        )
    except Exception as e:
        logger.error("Failed to list conversations: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to list conversations: {str(e)}"
        ) from e


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: ConversationCreate,
    repository: ConversationRepository = Depends(get_repository),
) -> ConversationResponse:
    """Create a new conversation with server-generated thread_id.

    The server generates a UUID for thread_id to ensure uniqueness and security.

    Args:
        request: ConversationCreate with optional title
        repository: Injected conversation repository

    Returns:
        ConversationResponse with created conversation details
    """
    try:
        conversation = await repository.create_conversation(title=request.title)
        return ConversationResponse(**conversation)
    except Exception as e:
        logger.error("Failed to create conversation: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create conversation: {str(e)}"
        ) from e


@router.get("/{thread_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    thread_id: Annotated[str, Path(min_length=1, max_length=100)],
    repository: ConversationRepository = Depends(get_repository),
) -> ConversationHistoryResponse:
    """Load conversation history from LangGraph checkpointer.

    This endpoint retrieves the conversation state from the checkpointer,
    including message history. If the checkpoint doesn't exist or fails to load,
    it returns an empty state (no crash).

    Args:
        thread_id: LangGraph thread identifier
        repository: Injected conversation repository

    Returns:
        ConversationHistoryResponse with message history and metadata

    Raises:
        HTTPException: 404 if conversation not found in database
    """
    try:
        # Verify conversation exists in database
        conversation = await repository.get_conversation(thread_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {thread_id} not found")

        # Check if conversation is deleted
        if conversation.get("is_deleted", False):
            raise HTTPException(status_code=404, detail=f"Conversation {thread_id} not found")

        # Load checkpoint from LangGraph
        try:
            from src.retrieval_graph.graph import graph as retrieval_graph

            config = RunnableConfig(configurable={"thread_id": thread_id})

            # Use get_state to retrieve the current state from checkpointer
            state = await retrieval_graph.aget_state(config)

            # Extract messages from state if they exist
            messages = []
            if state and state.values:
                raw_messages = state.values.get("messages", [])
                # Convert messages to serializable dicts
                for msg in raw_messages:
                    if hasattr(msg, "dict"):
                        messages.append(msg.dict())
                    elif hasattr(msg, "content") and hasattr(msg, "type"):
                        messages.append({"content": msg.content, "type": msg.type})
                    elif isinstance(msg, dict):
                        messages.append(msg)
                    else:
                        messages.append({"content": str(msg), "type": "unknown"})

            # Handle metadata - convert to dict if needed
            # CheckpointMetadata is not a dict, so we need special handling
            metadata_dict: dict[str, Any] = {}
            if state and hasattr(state, "metadata") and state.metadata is not None:
                if isinstance(state.metadata, dict):
                    metadata_dict = state.metadata  # type: ignore[assignment]
                else:
                    # CheckpointMetadata - convert to dict or use fallback
                    try:
                        metadata_dict = dict(state.metadata)
                    except (TypeError, ValueError):
                        # Fallback for non-convertible metadata
                        metadata_dict = {"raw": str(state.metadata)}

            return ConversationHistoryResponse(
                threadId=thread_id, messages=messages, metadata=metadata_dict
            )
        except Exception as checkpoint_error:
            # Distinguish error types for better debugging
            error_msg = str(checkpoint_error).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                logger.info("No checkpoint found for thread %s, returning empty state", thread_id)
            else:
                logger.warning(
                    "Failed to load checkpoint for thread %s: %s",
                    thread_id,
                    str(checkpoint_error),
                )
            return ConversationHistoryResponse(threadId=thread_id, messages=[], metadata={})

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation history: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get conversation history: {str(e)}"
        ) from e


@router.patch("/{thread_id}", response_model=ConversationResponse)
async def update_conversation(
    thread_id: Annotated[str, Path(min_length=1, max_length=100)],
    request: ConversationUpdate,
    repository: ConversationRepository = Depends(get_repository),
) -> ConversationResponse:
    """Update a conversation's title.

    Args:
        thread_id: LangGraph thread identifier
        request: ConversationUpdate with new title
        repository: Injected conversation repository

    Returns:
        ConversationResponse with updated conversation details

    Raises:
        HTTPException: 404 if conversation not found or already deleted
    """
    try:
        conversation = await repository.update_conversation(thread_id, request.title)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {thread_id} not found or already deleted",
            )
        return ConversationResponse(**conversation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update conversation: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update conversation: {str(e)}"
        ) from e


@router.delete("/{thread_id}", response_model=DeleteResponse)
async def delete_conversation(
    thread_id: Annotated[str, Path(min_length=1, max_length=100)],
    repository: ConversationRepository = Depends(get_repository),
) -> DeleteResponse:
    """Soft delete a conversation by setting is_deleted flag.

    This endpoint does not delete checkpoints or messages, only marks
    the conversation as deleted in the database.

    Args:
        thread_id: LangGraph thread identifier
        repository: Injected conversation repository

    Returns:
        DeleteResponse with success status

    Raises:
        HTTPException: 404 if conversation not found or already deleted
    """
    try:
        deleted = await repository.soft_delete_conversation(thread_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {thread_id} not found or already deleted",
            )
        return DeleteResponse(
            success=True,
            message=f"Conversation {thread_id} deleted successfully",
            threadId=thread_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete conversation: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete conversation: {str(e)}"
        ) from e
