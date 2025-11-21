'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from 'react';
import { useToast } from '@/hooks/use-toast';
import type {
  Conversation,
  ConversationListResponse,
} from '@/types/conversation';

interface ConversationContextValue {
  conversations: Conversation[];
  currentThreadId: string | null;
  isLoading: boolean;
  error: string | null;
  setCurrentThreadId: (threadId: string | null) => void;
  createConversation: (title?: string) => Promise<Conversation | null>;
  deleteConversation: (threadId: string) => Promise<boolean>;
  refreshConversations: () => Promise<void>;
  updateConversationTitle: (threadId: string, title: string) => Promise<void>;
}

const ConversationContext = createContext<ConversationContextValue | undefined>(
  undefined
);

const STORAGE_KEY = 'currentThreadId';
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export function ConversationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { toast } = useToast();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentThreadId, setCurrentThreadIdState] = useState<string | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isInitialMount = useRef(true);

  // Load conversations from API
  const loadConversations = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/conversations?limit=100`);

      if (!response.ok) {
        throw new Error(`Failed to load conversations: ${response.status}`);
      }

      const data: ConversationListResponse = await response.json();
      setConversations(data.conversations);

      return data.conversations;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to load conversations';
      setError(errorMessage);
      console.error('Error loading conversations:', err);
      return [];
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize: Load conversations and restore/set currentThreadId
  useEffect(() => {
    const initialize = async () => {
      const loadedConversations = await loadConversations();

      // Try to restore thread ID from localStorage
      const storedThreadId = localStorage.getItem(STORAGE_KEY);

      if (storedThreadId) {
        // Verify the stored thread ID exists in loaded conversations
        const exists = loadedConversations.some(
          (c) => c.threadId === storedThreadId
        );
        if (exists) {
          setCurrentThreadIdState(storedThreadId);
          return;
        }
      }

      // If no valid stored thread ID, select the most recent or create new
      if (loadedConversations.length > 0) {
        setCurrentThreadIdState(loadedConversations[0].threadId);
      } else {
        // No conversations exist, create a new one
        const newConversation = await createConversationInternal();
        if (newConversation) {
          setCurrentThreadIdState(newConversation.threadId);
        }
      }
    };

    if (isInitialMount.current) {
      isInitialMount.current = false;
      initialize();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Persist currentThreadId to localStorage whenever it changes
  useEffect(() => {
    if (currentThreadId) {
      localStorage.setItem(STORAGE_KEY, currentThreadId);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [currentThreadId]);

  // Internal create conversation helper (no toast)
  const createConversationInternal = async (
    title?: string
  ): Promise<Conversation | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title || null }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create conversation: ${response.status}`);
      }

      const conversation: Conversation = await response.json();

      // Add to list at the top (most recent)
      setConversations((prev) => [conversation, ...prev]);

      return conversation;
    } catch (err) {
      console.error('Error creating conversation:', err);
      return null;
    }
  };

  // Public create conversation (with toast)
  const createConversation = async (
    title?: string
  ): Promise<Conversation | null> => {
    try {
      const conversation = await createConversationInternal(title);

      if (!conversation) {
        throw new Error('Failed to create conversation');
      }

      toast({
        title: 'New conversation',
        description: 'Started a new conversation',
      });

      return conversation;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to create conversation';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
      return null;
    }
  };

  // Delete conversation
  const deleteConversation = async (threadId: string): Promise<boolean> => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/conversations/${threadId}`,
        {
          method: 'DELETE',
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to delete conversation: ${response.status}`);
      }

      // Remove from local state
      setConversations((prev) => prev.filter((c) => c.threadId !== threadId));

      // If deleted conversation was active, select next or create new
      if (currentThreadId === threadId) {
        const remaining = conversations.filter((c) => c.threadId !== threadId);

        if (remaining.length > 0) {
          // Select the next most recent conversation
          setCurrentThreadIdState(remaining[0].threadId);
        } else {
          // No conversations left, create a new one
          const newConversation = await createConversationInternal();
          if (newConversation) {
            setCurrentThreadIdState(newConversation.threadId);
          } else {
            setCurrentThreadIdState(null);
          }
        }
      }

      toast({
        title: 'Conversation deleted',
        description: 'The conversation has been removed',
      });

      return true;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to delete conversation';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
      return false;
    }
  };

  // Refresh conversations list
  const refreshConversations = async () => {
    await loadConversations();
  };

  // Update conversation title
  const updateConversationTitle = async (threadId: string, title: string) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/conversations/${threadId}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update conversation: ${response.status}`);
      }

      const updated: Conversation = await response.json();

      // Update in local state
      setConversations((prev) =>
        prev.map((c) => (c.threadId === threadId ? updated : c))
      );

      toast({
        title: 'Title updated',
        description: 'Conversation title has been updated',
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update conversation';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  // Public setter for currentThreadId
  const setCurrentThreadId = (threadId: string | null) => {
    setCurrentThreadIdState(threadId);
  };

  const value: ConversationContextValue = {
    conversations,
    currentThreadId,
    isLoading,
    error,
    setCurrentThreadId,
    createConversation,
    deleteConversation,
    refreshConversations,
    updateConversationTitle,
  };

  return (
    <ConversationContext.Provider value={value}>
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversations() {
  const context = useContext(ConversationContext);
  if (context === undefined) {
    throw new Error(
      'useConversations must be used within a ConversationProvider'
    );
  }
  return context;
}
