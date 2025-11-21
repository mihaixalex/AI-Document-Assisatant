import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { ConversationProvider, useConversations } from '@/contexts/ConversationContext';

// Mock fetch globally
global.fetch = jest.fn();

// Mock useToast
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('ConversationContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
    (global.fetch as jest.Mock).mockClear();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <ConversationProvider>{children}</ConversationProvider>
  );

  const mockConversations = [
    {
      id: '1',
      threadId: 'thread-1',
      title: 'Test Conversation 1',
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-01T00:00:00Z',
      userId: null,
      isDeleted: false,
    },
    {
      id: '2',
      threadId: 'thread-2',
      title: 'Test Conversation 2',
      createdAt: '2025-01-02T00:00:00Z',
      updatedAt: '2025-01-02T00:00:00Z',
      userId: null,
      isDeleted: false,
    },
  ];

  it('should throw error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useConversations());
    }).toThrow('useConversations must be used within a ConversationProvider');

    consoleError.mockRestore();
  });

  it('should load conversations on mount', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conversations: mockConversations,
        total: 2,
        limit: 100,
        offset: 0,
      }),
    });

    const { result } = renderHook(() => useConversations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.conversations).toEqual(mockConversations);
    expect(result.current.currentThreadId).toBe('thread-1');
  });

  it('should create a new conversation when none exist', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          conversations: [],
          total: 0,
          limit: 100,
          offset: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockConversations[0],
      });

    const { result } = renderHook(() => useConversations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.conversations.length).toBeGreaterThan(0);
  });

  it('should create a new conversation', async () => {
    const newConversation = {
      id: '3',
      threadId: 'thread-3',
      title: 'New Conversation',
      createdAt: '2025-01-03T00:00:00Z',
      updatedAt: '2025-01-03T00:00:00Z',
      userId: null,
      isDeleted: false,
    };

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          conversations: mockConversations,
          total: 2,
          limit: 100,
          offset: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => newConversation,
      });

    const { result } = renderHook(() => useConversations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.createConversation('New Conversation');
    });

    expect(result.current.conversations).toContainEqual(newConversation);
  });

  it('should delete a conversation', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          conversations: mockConversations,
          total: 2,
          limit: 100,
          offset: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Deleted',
          threadId: 'thread-1',
        }),
      });

    const { result } = renderHook(() => useConversations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.deleteConversation('thread-1');
    });

    expect(result.current.conversations).not.toContainEqual(
      expect.objectContaining({ threadId: 'thread-1' })
    );
  });

  it('should switch to next conversation when deleting active conversation', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          conversations: mockConversations,
          total: 2,
          limit: 100,
          offset: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Deleted',
          threadId: 'thread-1',
        }),
      });

    const { result } = renderHook(() => useConversations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.currentThreadId).toBe('thread-1');

    await act(async () => {
      await result.current.deleteConversation('thread-1');
    });

    expect(result.current.currentThreadId).toBe('thread-2');
  });

  it('should persist currentThreadId to localStorage', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conversations: mockConversations,
        total: 2,
        limit: 100,
        offset: 0,
      }),
    });

    const { result } = renderHook(() => useConversations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.setCurrentThreadId('thread-2');
    });

    await waitFor(() => {
      expect(localStorageMock.getItem('currentThreadId')).toBe('thread-2');
    });
  });

  it('should handle API errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    const { result } = renderHook(() => useConversations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
  });

  it('should refresh conversations', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          conversations: mockConversations,
          total: 2,
          limit: 100,
          offset: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          conversations: [mockConversations[0]],
          total: 1,
          limit: 100,
          offset: 0,
        }),
      });

    const { result } = renderHook(() => useConversations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.conversations).toHaveLength(2);

    await act(async () => {
      await result.current.refreshConversations();
    });

    await waitFor(() => {
      expect(result.current.conversations).toHaveLength(1);
    });
  });
});
