import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConversationItem } from '@/components/conversation-item';
import type { Conversation } from '@/types/conversation';

describe('ConversationItem', () => {
  const mockConversation: Conversation = {
    id: '1',
    threadId: 'thread-1',
    title: 'Test Conversation',
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: new Date().toISOString(), // Recent timestamp
    userId: null,
    isDeleted: false,
  };

  const mockOnClick = jest.fn();
  const mockOnDelete = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render conversation title', () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('Test Conversation')).toBeInTheDocument();
  });

  it('should render "New Conversation" when title is null', () => {
    const conversationWithoutTitle = { ...mockConversation, title: null };

    render(
      <ConversationItem
        conversation={conversationWithoutTitle}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('New Conversation')).toBeInTheDocument();
  });

  it('should truncate long titles to 40 characters', () => {
    const longTitle = 'This is a very long conversation title that should be truncated';
    const conversationWithLongTitle = { ...mockConversation, title: longTitle };

    render(
      <ConversationItem
        conversation={conversationWithLongTitle}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    expect(
      screen.getByText(`${longTitle.substring(0, 40)}...`)
    ).toBeInTheDocument();
  });

  it('should display relative timestamp', () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    // Should show something like "less than a minute ago"
    expect(screen.getByText(/ago/i)).toBeInTheDocument();
  });

  it('should call onClick when clicked', () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    const item = screen.getByRole('button', {
      name: /select conversation: test conversation/i,
    });
    fireEvent.click(item);

    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it('should handle keyboard navigation (Enter key)', () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    const item = screen.getByRole('button', {
      name: /select conversation: test conversation/i,
    });
    fireEvent.keyDown(item, { key: 'Enter' });

    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it('should handle keyboard navigation (Space key)', () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    const item = screen.getByRole('button', {
      name: /select conversation: test conversation/i,
    });
    fireEvent.keyDown(item, { key: ' ' });

    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it('should highlight active conversation', () => {
    const { container } = render(
      <ConversationItem
        conversation={mockConversation}
        isActive={true}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    const item = screen.getByRole('button', {
      name: /select conversation: test conversation/i,
    });

    // Check for active styling (border-primary class)
    expect(item).toHaveClass('border-primary');
  });

  it('should show delete button', () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    const deleteButton = screen.getByRole('button', {
      name: /delete conversation test conversation/i,
    });

    expect(deleteButton).toBeInTheDocument();
  });

  it('should show delete confirmation dialog when delete button is clicked', async () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    const deleteButton = screen.getByRole('button', {
      name: /delete conversation test conversation/i,
    });
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(screen.getByText('Delete conversation?')).toBeInTheDocument();
    });
  });

  it('should not call onClick when delete button is clicked', () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    const deleteButton = screen.getByRole('button', {
      name: /delete conversation test conversation/i,
    });
    fireEvent.click(deleteButton);

    expect(mockOnClick).not.toHaveBeenCalled();
  });

  it('should call onDelete when deletion is confirmed', async () => {
    mockOnDelete.mockResolvedValue(undefined);

    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    // Open delete dialog
    const deleteButton = screen.getByRole('button', {
      name: /delete conversation test conversation/i,
    });
    fireEvent.click(deleteButton);

    // Confirm deletion
    await waitFor(() => {
      expect(screen.getByText('Delete conversation?')).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole('button', { name: /^delete$/i });
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(mockOnDelete).toHaveBeenCalledWith('thread-1');
    });
  });

  it('should not call onDelete when deletion is cancelled', async () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    // Open delete dialog
    const deleteButton = screen.getByRole('button', {
      name: /delete conversation test conversation/i,
    });
    fireEvent.click(deleteButton);

    // Cancel deletion
    await waitFor(() => {
      expect(screen.getByText('Delete conversation?')).toBeInTheDocument();
    });

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnDelete).not.toHaveBeenCalled();
  });

  it('should have accessible ARIA labels', () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    expect(
      screen.getByRole('button', {
        name: /select conversation: test conversation/i,
      })
    ).toBeInTheDocument();

    expect(
      screen.getByRole('button', {
        name: /delete conversation test conversation/i,
      })
    ).toBeInTheDocument();
  });

  it('should meet 44px touch target requirement on mobile', () => {
    render(
      <ConversationItem
        conversation={mockConversation}
        isActive={false}
        onClick={mockOnClick}
        onDelete={mockOnDelete}
      />
    );

    const item = screen.getByRole('button', {
      name: /select conversation: test conversation/i,
    });

    // Check for min-h-[44px] class
    expect(item).toHaveClass('min-h-[44px]');
  });
});
