'use client';

import React, { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { MessageSquare, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useConversation, type Conversation } from '@/contexts/conversation-context';
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
import { Button } from '@/components/ui/button';
import {
  SidebarMenuItem,
  SidebarMenuButton,
  useSidebar,
} from '@/components/ui/sidebar';

interface ConversationItemProps {
  conversation: Conversation;
}

export function ConversationItem({ conversation }: ConversationItemProps) {
  const { currentThreadId, loadConversation, deleteConversation } = useConversation();
  const { setOpenMobile, isMobile } = useSidebar();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const isActive = currentThreadId === conversation.threadId;

  // Truncate title to 40 characters (handle null/undefined)
  const title = conversation.title || 'Untitled';
  const truncatedTitle = title.length > 40
    ? title.substring(0, 40) + '...'
    : title;

  // Format relative timestamp
  const relativeTime = formatDistanceToNow(new Date(conversation.updatedAt), {
    addSuffix: true,
  });

  const handleClick = () => {
    loadConversation(conversation.threadId);
    if (isMobile) {
      setOpenMobile(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteDialog(true);
  };

  const confirmDelete = async () => {
    setIsDeleting(true);
    try {
      await deleteConversation(conversation.threadId);
      setShowDeleteDialog(false);
    } catch (error) {
      console.error('Error deleting conversation:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <SidebarMenuItem>
        <div className="group/item relative flex items-center w-full">
          <SidebarMenuButton
            onClick={handleClick}
            isActive={isActive}
            className={cn(
              'w-full justify-start',
              isActive && 'border-l-2 border-primary'
            )}
            aria-label={`Load conversation: ${conversation.title}`}
          >
            <MessageSquare className="h-4 w-4 shrink-0" />
            <div className="flex flex-col items-start overflow-hidden flex-1 min-w-0">
              <span className="text-sm font-medium truncate w-full">
                {truncatedTitle}
              </span>
              <span className="text-xs text-muted-foreground">
                {relativeTime}
              </span>
            </div>
          </SidebarMenuButton>

          {/* Delete button - shows on hover (desktop) or always when active */}
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              'absolute right-2 h-8 w-8 transition-all z-10',
              // Use opacity pattern for hover visibility
              'opacity-0 group-hover/item:opacity-100',
              'hover:bg-destructive hover:text-destructive-foreground',
              // Always visible when active
              isActive && 'opacity-100'
            )}
            onClick={handleDelete}
            aria-label={`Delete conversation: ${conversation.title}`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </SidebarMenuItem>

      {/* Delete confirmation dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{title}&quot;? This action cannot be undone.
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
