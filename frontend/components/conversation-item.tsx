'use client';

import React, { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import type { Conversation } from '@/types/conversation';
import { cn } from '@/lib/utils';

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onClick: () => void;
  onDelete: (threadId: string) => Promise<void>;
}

export function ConversationItem({
  conversation,
  isActive,
  onClick,
  onDelete,
}: ConversationItemProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteDialog(true);
  };

  const confirmDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(conversation.threadId);
      setShowDeleteDialog(false);
    } finally {
      setIsDeleting(false);
    }
  };

  // Format title: truncate to 40 chars or use "New Conversation"
  const displayTitle = conversation.title
    ? conversation.title.length > 40
      ? `${conversation.title.substring(0, 40)}...`
      : conversation.title
    : 'New Conversation';

  // Format relative timestamp
  const relativeTime = formatDistanceToNow(new Date(conversation.updatedAt), {
    addSuffix: true,
  });

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        aria-label={`Select conversation: ${displayTitle}`}
        className={cn(
          'group relative flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all',
          'hover:bg-accent focus:bg-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'min-h-[44px] md:min-h-0', // 44px touch target on mobile
          isActive && 'bg-accent border-l-2 border-primary'
        )}
        onClick={onClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClick();
          }
        }}
      >
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate text-foreground">
            {displayTitle}
          </p>
          <p className="text-xs text-muted-foreground truncate">
            {relativeTime}
          </p>
        </div>

        {/* Delete button - show on hover (desktop) or always (mobile) */}
        <div
          className={cn(
            'flex items-center',
            'md:opacity-0 md:group-hover:opacity-100',
            'transition-opacity'
          )}
        >
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0"
            onClick={handleDelete}
            aria-label={`Delete conversation ${displayTitle}`}
            disabled={isDeleting}
          >
            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
          </Button>
        </div>
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete &quot;{displayTitle}&quot; and all its
              messages. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
