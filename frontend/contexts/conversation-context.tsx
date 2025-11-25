'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { useToast } from '@/hooks/use-toast';

export interface Conversation {
  id: string;
  threadId: string;
  title: string | null;
  createdAt: string;
  updatedAt: string;
}

interface ConversationContextType {
  conversations: Conversation[];
  currentThreadId: string | null;
  isLoading: boolean;
  isHydrated: boolean;
  error: string | null;
  createConversation: (title?: string) => Promise<Conversation>;
  loadConversation: (threadId: string) => Promise<void>;
  deleteConversation: (threadId: string) => Promise<void>;
  updateConversation: (threadId: string, title: string) => Promise<Conversation>;
  refreshConversations: () => Promise<void>;
  setCurrentThreadId: (threadId: string | null) => void;
}

const ConversationContext = createContext<ConversationContextType | null>(null);

export function useConversation() {
  const context = useContext(ConversationContext);
  if (!context) {
    throw new Error('useConversation must be used within a ConversationProvider');
  }
  return context;
}

export function ConversationProvider({ children }: { children: ReactNode }) {
  const { toast } = useToast();

  // Initialize with null to avoid SSR hydration mismatch
  const [currentThreadId, setCurrentThreadIdState] = useState<string | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ref to capture hydrated threadId BEFORE any async operations (Context7 pattern)
  const hydratedThreadIdRef = useRef<string | null>(null);

  // Hydrate from localStorage after mount - capture value in ref immediately
  useEffect(() => {
    const stored = localStorage.getItem('currentThreadId');
    if (stored && stored.trim() !== '') {
      hydratedThreadIdRef.current = stored; // Capture in ref before state update
      setCurrentThreadIdState(stored);
    }
    setIsHydrated(true);
  }, []);

  // Persist currentThreadId to localStorage
  useEffect(() => {
    if (currentThreadId) {
      localStorage.setItem('currentThreadId', currentThreadId);
    } else {
      localStorage.removeItem('currentThreadId');
    }
  }, [currentThreadId]);

  // Wrapper to update state and localStorage
  const setCurrentThreadId = useCallback((threadId: string | null) => {
    setCurrentThreadIdState(threadId);
  }, []);

  // Fetch all conversations
  const refreshConversations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/conversations');
      if (!response.ok) {
        throw new Error('Failed to fetch conversations');
      }
      const data = await response.json();
      // Backend returns { conversations: [...], total, limit, offset }
      setConversations(data.conversations || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: 'Failed to load conversations',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  // Create a new conversation
  const createConversation = useCallback(async (title?: string): Promise<Conversation> => {
    try {
      const response = await fetch('/api/conversations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: title || 'New Conversation',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create conversation');
      }

      const newConversation = await response.json();

      // Add to conversations list
      setConversations((prev) => [newConversation, ...prev]);

      // Set as current conversation
      setCurrentThreadId(newConversation.threadId);

      return newConversation;
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to create conversation',
        variant: 'destructive',
      });
      throw err;
    }
  }, [toast, setCurrentThreadId]);

  // Load a conversation (just sets it as current)
  const loadConversation = useCallback(async (threadId: string) => {
    setCurrentThreadId(threadId);
  }, [setCurrentThreadId]);

  // Delete a conversation
  const deleteConversation = useCallback(async (threadId: string) => {
    try {
      const response = await fetch(`/api/conversations/${encodeURIComponent(threadId)}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete conversation');
      }

      // Use functional state updates to avoid stale closure issues
      let needsNewConversation = false;

      setConversations(prev => {
        const remaining = prev.filter((c) => c.threadId !== threadId);
        // Capture if we need a new conversation (will be empty after delete)
        if (remaining.length === 0) {
          needsNewConversation = true;
        }
        return remaining;
      });

      setCurrentThreadIdState(prevThreadId => {
        // Only update if we're deleting the current conversation
        if (prevThreadId === threadId) {
          // We'll set to null and let the createConversation handle setting new one
          // OR use the first remaining conversation
          return null;
        }
        return prevThreadId;
      });

      // Create new conversation if needed (all conversations deleted)
      if (needsNewConversation) {
        await createConversation('New Conversation');
      } else {
        // If we deleted the current conversation but others remain, select the first one
        setConversations(prev => {
          if (prev.length > 0) {
            setCurrentThreadIdState(current => current === null ? prev[0].threadId : current);
          }
          return prev;
        });
      }

      toast({
        title: 'Conversation deleted',
        description: 'The conversation has been removed.',
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    }
  }, [toast, createConversation]);

  // Update a conversation's title
  const updateConversation = useCallback(async (threadId: string, title: string): Promise<Conversation> => {
    try {
      const response = await fetch(`/api/conversations/${encodeURIComponent(threadId)}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title }),
      });

      if (!response.ok) {
        throw new Error('Failed to update conversation');
      }

      const updatedConversation = await response.json();

      // Update in conversations list
      setConversations((prev) =>
        prev.map((c) => (c.threadId === threadId ? { ...c, title: updatedConversation.title, updatedAt: updatedConversation.updatedAt } : c))
      );

      toast({
        title: 'Conversation renamed',
        description: 'The conversation title has been updated.',
      });

      return updatedConversation;
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to update conversation',
        variant: 'destructive',
      });
      throw err;
    }
  }, [toast]);

  // Use ref to prevent multiple initialization runs
  const hasInitializedRef = useRef(false);

  // Single initialization effect - runs once after hydration
  useEffect(() => {
    // Only run once and only after hydration is complete
    if (hasInitializedRef.current || !isHydrated) return;
    hasInitializedRef.current = true;

    let mounted = true;

    const initialize = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch conversations from backend
        const response = await fetch('/api/conversations');
        if (!response.ok) {
          throw new Error('Failed to fetch conversations');
        }
        const data = await response.json();
        const fetchedConversations: Conversation[] = data.conversations || [];

        if (!mounted) return;

        // Update conversations state
        setConversations(fetchedConversations);

        // Use ref value (captured at hydration) instead of state to avoid stale closure
        const storedThreadId = hydratedThreadIdRef.current;

        if (fetchedConversations.length === 0) {
          // No conversations exist - create one
          // But DON'T use the callback since we need to avoid stale state
          const createResponse = await fetch('/api/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New Conversation' }),
          });

          if (!createResponse.ok) {
            throw new Error('Failed to create initial conversation');
          }

          const newConv = await createResponse.json();
          if (mounted) {
            setConversations([newConv]);
            setCurrentThreadIdState(newConv.threadId);
          }
        } else if (storedThreadId) {
          // We have a stored threadId - validate it exists
          const exists = fetchedConversations.some((c) => c.threadId === storedThreadId);
          if (!exists) {
            // Stored threadId is invalid - use first conversation
            if (mounted) {
              setCurrentThreadIdState(fetchedConversations[0].threadId);
            }
          }
          // If exists, currentThreadId is already set from hydration - keep it
        } else {
          // No stored threadId but conversations exist - use first one
          if (mounted) {
            setCurrentThreadIdState(fetchedConversations[0].threadId);
          }
        }
      } catch (error) {
        if (mounted) {
          const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          setError(errorMessage);
          toast({
            title: 'Error',
            description: 'Failed to load conversations',
            variant: 'destructive',
          });
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    initialize();

    return () => {
      mounted = false;
    };
  }, [isHydrated, toast]); // NO currentThreadId - use hydratedThreadIdRef instead to prevent race conditions

  const value: ConversationContextType = {
    conversations,
    currentThreadId,
    isLoading,
    isHydrated,
    error,
    createConversation,
    loadConversation,
    deleteConversation,
    updateConversation,
    refreshConversations,
    setCurrentThreadId,
  };

  return (
    <ConversationContext.Provider value={value}>
      {children}
    </ConversationContext.Provider>
  );
}
