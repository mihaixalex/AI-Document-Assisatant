"""Pydantic models for conversation API endpoints.

This module defines request and response models for the conversation management API.
All models use Pydantic for validation and serialization.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationBase(BaseModel):
    """Base model for conversation data shared across requests/responses."""

    title: str | None = Field(default=None, max_length=500, description="Conversation title")


class ConversationCreate(BaseModel):
    """Request model for creating a new conversation.

    Server generates thread_id automatically, so this model is minimal.
    """

    title: str | None = Field(
        default=None, max_length=500, description="Optional initial conversation title"
    )


class ConversationUpdate(BaseModel):
    """Request model for updating conversation metadata."""

    title: str = Field(..., min_length=1, max_length=500, description="Updated conversation title")


class ConversationResponse(BaseModel):
    """Response model for conversation metadata."""

    id: UUID = Field(..., description="Internal database ID")
    thread_id: str = Field(..., alias="threadId", description="LangGraph thread identifier")
    title: str | None = Field(default=None, description="Conversation title")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update timestamp")
    user_id: str | None = Field(default=None, alias="userId", description="User identifier")
    is_deleted: bool = Field(..., alias="isDeleted", description="Soft delete flag")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class DeletedConversationResponse(BaseModel):
    """Response model for deleted conversation with expiration info."""

    id: UUID = Field(..., description="Internal database ID")
    thread_id: str = Field(..., alias="threadId", description="LangGraph thread identifier")
    title: str | None = Field(default=None, description="Conversation title")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update timestamp")
    user_id: str | None = Field(default=None, alias="userId", description="User identifier")
    is_deleted: bool = Field(..., alias="isDeleted", description="Soft delete flag")
    deleted_at: datetime | None = Field(default=None, alias="deletedAt", description="Deletion timestamp")
    expires_at: datetime | None = Field(default=None, alias="expiresAt", description="Permanent deletion time")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class DeletedConversationListResponse(BaseModel):
    """Response model for deleted conversations list with pagination."""

    conversations: list[DeletedConversationResponse] = Field(..., description="List of deleted conversations")
    total: int = Field(..., description="Total count of deleted conversations")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Pagination offset")


class ConversationListResponse(BaseModel):
    """Response model for list endpoint with pagination metadata."""

    conversations: list[ConversationResponse] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total count of non-deleted conversations")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Pagination offset")


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history loaded from checkpointer."""

    thread_id: str = Field(..., alias="threadId", description="LangGraph thread identifier")
    messages: list[dict[str, Any]] = Field(default_factory=list, description="Message history")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional checkpoint metadata"
    )

    model_config = ConfigDict(populate_by_name=True)


class DeleteResponse(BaseModel):
    """Response model for successful deletion."""

    success: bool = Field(default=True, description="Deletion success status")
    message: str = Field(..., description="Success message")
    thread_id: str = Field(..., alias="threadId", description="Deleted thread identifier")

    model_config = ConfigDict(populate_by_name=True)
