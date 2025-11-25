'use client';

import React, { useState, useRef, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { MessageSquare, Trash2, Pencil, Check, X } from 'lucide-react';
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

interface ConversationItemProps {
  conversation: Conversation;
}

export function ConversationItem({ conversation }: ConversationItemProps) {
  const { currentThreadId, loadConversation, deleteConversation, updateConversation } = useConversation();

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const isActive = currentThreadId === conversation.threadId;
  const title = conversation.title || 'Untitled';

  const relativeTime = formatDistanceToNow(new Date(conversation.updatedAt), { addSuffix: true });

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleClick = () => {
    if (isEditing) return;
    loadConversation(conversation.threadId);
  };

  const handleStartEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setEditTitle(title);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditTitle('');
  };

  const handleSaveEdit = async () => {
    const trimmedTitle = editTitle.trim();
    if (!trimmedTitle || trimmedTitle === title) {
      handleCancelEdit();
      return;
    }

    setIsSaving(true);
    try {
      await updateConversation(conversation.threadId, trimmedTitle);
      setIsEditing(false);
      setEditTitle('');
    } catch (error) {
      console.error('Error updating conversation:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleCancelEdit();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveEdit();
    }
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
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

  // Edit mode
  if (isEditing) {
    return (
      <div className="flex items-center gap-1 p-2 rounded-md bg-[#1F1F1F]">
        <input
          ref={inputRef}
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSaving}
          className="h-8 text-sm flex-1 bg-[#0D0D0D] border border-[#333333] rounded px-2 text-white placeholder-[#666666] focus:outline-none focus:border-[#00FF9D]"
          maxLength={100}
        />
        <button
          type="button"
          disabled={isSaving || !editTitle.trim()}
          onClick={handleSaveEdit}
          className="h-8 w-8 flex items-center justify-center text-[#00FF9D] hover:bg-[#2F2F2F] rounded disabled:opacity-50"
          aria-label="Save"
        >
          <Check className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleCancelEdit}
          disabled={isSaving}
          className="h-8 w-8 flex items-center justify-center text-[#AAAAAA] hover:bg-[#2F2F2F] rounded disabled:opacity-50"
          aria-label="Cancel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  // Normal mode - list item
  return (
    <>
      <div
        onClick={handleClick}
        className={cn(
          'group h-14 p-3 rounded-md cursor-pointer transition-colors',
          'hover:bg-[#1A1A1A]',
          isActive && 'bg-[#1F1F1F] border-l-4 border-[#00FF9D]'
        )}
        role="listitem"
        aria-current={isActive ? 'true' : undefined}
      >
        <div className="flex items-center justify-between h-full">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <MessageSquare className="h-4 w-4 shrink-0 text-[#AAAAAA]" />
            <div className="min-w-0 flex-1">
              <p className="font-medium truncate text-white text-sm">{title}</p>
              <p className="text-xs text-[#AAAAAA]">{relativeTime}</p>
            </div>
          </div>

          {/* Action buttons - visible on hover or when active */}
          <div className={cn(
            'flex items-center shrink-0 ml-2',
            'opacity-0 group-hover:opacity-100 transition-opacity',
            isActive && 'opacity-100'
          )}>
            <button
              type="button"
              onClick={handleStartEdit}
              className="h-7 w-7 flex items-center justify-center text-[#AAAAAA] hover:text-white hover:bg-[#2F2F2F] rounded transition-colors"
              aria-label="Edit conversation"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={handleDeleteClick}
              className="h-7 w-7 flex items-center justify-center text-[#AAAAAA] hover:text-red-400 hover:bg-red-900/30 rounded transition-colors"
              aria-label="Delete conversation"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-[#1F1F1F] border-[#333333]">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Delete Conversation</AlertDialogTitle>
            <AlertDialogDescription className="text-[#AAAAAA]">
              Delete &quot;{title}&quot;? You can restore it from the Deleted section within 30 days.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              disabled={isDeleting}
              className="bg-[#1F1F1F] border-[#333333] text-white hover:bg-[#2F2F2F]"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={isDeleting}
              className="bg-red-900 text-white hover:bg-red-800"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
