import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConversationSidebar } from '@/components/conversation-sidebar';
import { ConversationProvider } from '@/contexts/ConversationContext';
import type { Conversation } from '@/types/conversation';

// Mock fetch globally
global.fetch = jest.fn();

// Mock useToast
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock useIsMobile
jest.mock('@/components/ui/use-mobile', () => ({
  useIsMobile: jest.fn(() => false), // Default to desktop
}));

const mockConversations: Conversation[] = [
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

describe('ConversationSidebar', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  const renderWithProvider = (ui: React.ReactElement) => {
    return render(<ConversationProvider>{ui}</ConversationProvider>);
  };

  it('should render "New Chat" button', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conversations: mockConversations,
        total: 2,
        limit: 100,
        offset: 0,
      }),
    });

    renderWithProvider(<ConversationSidebar />);

    await waitFor(() => {
      expect(screen.getByText('New Chat')).toBeInTheDocument();
    });
  });

  it('should show loading skeleton while loading', async () => {
    let resolvePromise: any;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    (global.fetch as jest.Mock).mockReturnValue(promise);

    const { container } = renderWithProvider(<ConversationSidebar />);

    // Check that skeletons are rendered (they have animate-pulse class)
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);

    // Resolve the promise to complete the test
    resolvePromise({
      ok: true,
      json: async () => ({
        conversations: mockConversations,
        total: 2,
        limit: 100,
        offset: 0,
      }),
    });

    await waitFor(() => {
      expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
    });
  });

  it('should render conversations list', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conversations: mockConversations,
        total: 2,
        limit: 100,
        offset: 0,
      }),
    });

    renderWithProvider(<ConversationSidebar />);

    await waitFor(() => {
      expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
      expect(screen.getByText('Test Conversation 2')).toBeInTheDocument();
    });
  });

  it('should create a conversation when no conversations exist', async () => {
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

    renderWithProvider(<ConversationSidebar />);

    // Wait for the automatic conversation creation
    await waitFor(() => {
      expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
    });
  });

  it('should show error state on API failure', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    renderWithProvider(<ConversationSidebar />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load conversations')).toBeInTheDocument();
    });
  });

  it('should show retry button in error state', async () => {
    (global.fetch as jest.Mock)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          conversations: mockConversations,
          total: 2,
          limit: 100,
          offset: 0,
        }),
      });

    renderWithProvider(<ConversationSidebar />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load conversations')).toBeInTheDocument();
    });

    const retryButton = screen.getByRole('button', { name: /retry/i });
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
    });
  });

  it('should create new conversation when "New Chat" is clicked', async () => {
    const newConversation = {
      id: '3',
      threadId: 'thread-3',
      title: null,
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

    renderWithProvider(<ConversationSidebar />);

    await waitFor(() => {
      expect(screen.getByText('New Chat')).toBeInTheDocument();
    });

    const newChatButton = screen.getByRole('button', { name: /new chat/i });
    fireEvent.click(newChatButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/conversations'),
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  it('should have accessible navigation label', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conversations: mockConversations,
        total: 2,
        limit: 100,
        offset: 0,
      }),
    });

    renderWithProvider(<ConversationSidebar />);

    await waitFor(() => {
      expect(
        screen.getByRole('navigation', { name: /conversation history/i })
      ).toBeInTheDocument();
    });
  });

  it('should render as fixed sidebar on desktop', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conversations: mockConversations,
        total: 2,
        limit: 100,
        offset: 0,
      }),
    });

    const { container } = renderWithProvider(<ConversationSidebar />);

    await waitFor(() => {
      expect(screen.getByText('New Chat')).toBeInTheDocument();
    });

    const sidebar = container.querySelector('aside');
    expect(sidebar).toBeInTheDocument();
    expect(sidebar).toHaveClass('w-[280px]');
  });

  it('should render with fade-in animation', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conversations: mockConversations,
        total: 2,
        limit: 100,
        offset: 0,
      }),
    });

    renderWithProvider(<ConversationSidebar />);

    await waitFor(() => {
      expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
    });

    const list = screen
      .getByText('Test Conversation 1')
      .closest('.animate-in');
    expect(list).toHaveClass('fade-in');
  });
});

describe('ConversationSidebar - Mobile', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();

    // Mock useIsMobile to return true for mobile tests
    const useIsMobile = require('@/components/ui/use-mobile').useIsMobile;
    useIsMobile.mockReturnValue(true);
  });

  const renderWithProvider = (ui: React.ReactElement) => {
    return render(<ConversationProvider>{ui}</ConversationProvider>);
  };

  it('should render hamburger menu trigger on mobile', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conversations: mockConversations,
        total: 2,
        limit: 100,
        offset: 0,
      }),
    });

    renderWithProvider(<ConversationSidebar />);

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /open conversation menu/i })
      ).toBeInTheDocument();
    });
  });
});
