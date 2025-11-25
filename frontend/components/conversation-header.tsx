'use client';

import React, { useState } from 'react';
import { Plus, Loader2 } from 'lucide-react';
import { useConversation } from '@/contexts/conversation-context';
import { useIsMobile } from '@/hooks/use-mobile';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

export function ConversationHeader() {
  const { conversations, currentThreadId, createConversation } = useConversation();
  const isMobile = useIsMobile();
  const [isCreating, setIsCreating] = useState(false);

  // Find current conversation
  const currentConversation = conversations.find(
    (c) => c.threadId === currentThreadId
  );

  const handleNewChat = async () => {
    if (isCreating) return;
    setIsCreating(true);
    try {
      await createConversation('New Conversation');
    } catch (error) {
      console.error('Error creating conversation:', error);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <header className="flex h-14 items-center gap-2 px-4 border-b">
      {/* Mobile: Hamburger menu trigger */}
      <SidebarTrigger className="md:hidden" aria-label="Toggle sidebar" />

      {/* Current conversation title */}
      <div className="flex-1 flex items-center gap-2 min-w-0">
        <h1 className="text-lg font-semibold truncate">
          {currentConversation?.title ?? 'New Conversation'}
        </h1>
      </div>

      {/* Mobile: New Chat button */}
      {isMobile && (
        <>
          <Separator orientation="vertical" className="h-6" />
          <Button
            onClick={handleNewChat}
            size="icon"
            variant="ghost"
            disabled={isCreating}
            aria-label="Start new conversation"
          >
            {isCreating ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Plus className="h-5 w-5" />
            )}
          </Button>
        </>
      )}
    </header>
  );
}
