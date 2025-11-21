/**
 * TypeScript types for conversation management.
 * These types match the Pydantic models from backend/src/conversations/models.py
 */

/**
 * Conversation metadata from database
 */
export interface Conversation {
  id: string;
  threadId: string;
  title: string | null;
  createdAt: string; // ISO timestamp
  updatedAt: string; // ISO timestamp
  userId: string | null;
  isDeleted: boolean;
}

/**
 * Request body for creating a new conversation
 */
export interface ConversationCreateRequest {
  title?: string | null;
}

/**
 * Request body for updating a conversation
 */
export interface ConversationUpdateRequest {
  title: string;
}

/**
 * Response from list conversations endpoint
 */
export interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Message in conversation history
 */
export interface ConversationMessage {
  content: string;
  type: 'human' | 'assistant' | 'unknown';
  [key: string]: any;
}

/**
 * Response from conversation history endpoint
 */
export interface ConversationHistoryResponse {
  threadId: string;
  messages: ConversationMessage[];
  metadata: Record<string, any>;
}

/**
 * Response from delete endpoint
 */
export interface DeleteConversationResponse {
  success: boolean;
  message: string;
  threadId: string;
}
