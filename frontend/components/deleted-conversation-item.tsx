'use client';

import React, { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { MessageSquare, RotateCcw, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useConversation, type DeletedConversation } from '@/contexts/conversation-context';

interface DeletedConversationItemProps {
  conversation: DeletedConversation;
}

export function DeletedConversationItem({ conversation }: DeletedConversationItemProps) {
  const { restoreConversation } = useConversation();
  const [isRestoring, setIsRestoring] = useState(false);

  const title = conversation.title || 'Untitled';

  // Calculate time until permanent deletion
  const expiresAt = conversation.expiresAt ? new Date(conversation.expiresAt) : null;
  const expiresIn = expiresAt
    ? formatDistanceToNow(expiresAt, { addSuffix: false })
    : 'unknown';

  const handleRestore = async (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    if (isRestoring) return;

    setIsRestoring(true);
    try {
      await restoreConversation(conversation.threadId);
    } catch (error) {
      console.error('Error restoring conversation:', error);
    } finally {
      setIsRestoring(false);
    }
  };

  return (
    <div
      className={cn(
        'group h-14 p-3 rounded-md transition-colors',
        'hover:bg-[#1A1A1A] opacity-60 hover:opacity-100'
      )}
      role="listitem"
    >
      <div className="flex items-center justify-between h-full">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <MessageSquare className="h-4 w-4 shrink-0 text-[#666666]" />
          <div className="min-w-0 flex-1">
            <p className="font-medium truncate text-[#888888] text-sm line-through">{title}</p>
            <p className="text-xs text-[#666666]">Expires in {expiresIn}</p>
          </div>
        </div>

        {/* Restore button */}
        <div className="flex items-center shrink-0 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            type="button"
            onClick={handleRestore}
            disabled={isRestoring}
            className="h-7 px-2 flex items-center justify-center gap-1 text-[#00FF9D] hover:bg-[#00FF9D]/10 rounded transition-colors disabled:opacity-50"
            aria-label="Restore conversation"
          >
            {isRestoring ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <>
                <RotateCcw className="h-3.5 w-3.5" />
                <span className="text-xs">Restore</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
