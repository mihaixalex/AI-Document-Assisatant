'use client';

import React, { useState } from 'react';
import { Plus, MessageSquare, Loader2 } from 'lucide-react';
import { useConversation } from '@/contexts/conversation-context';
import { ConversationItem } from '@/components/conversation-item';
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
} from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';

export function ConversationSidebar() {
  const { conversations, isLoading, error, createConversation, refreshConversations } = useConversation();
  const [isCreating, setIsCreating] = useState(false);

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
    <Sidebar side="left" variant="sidebar" collapsible="offcanvas">
      {/* Header with New Chat button */}
      <SidebarHeader>
        <Button
          onClick={handleNewChat}
          className="w-full justify-start gap-2"
          variant="outline"
          disabled={isCreating}
          aria-label="Start new conversation"
        >
          {isCreating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
          <span>{isCreating ? 'Creating...' : 'New Chat'}</span>
        </Button>
      </SidebarHeader>

      {/* Content area with conversations list */}
      <SidebarContent>
        <ScrollArea className="flex-1">
          {/* Loading state */}
          {isLoading && conversations.length === 0 && (
            <div className="space-y-2 p-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-2 p-2">
                  <Skeleton className="h-4 w-4 rounded" />
                  <div className="flex-1 space-y-1">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Error state */}
          {error && !isLoading && (
            <div className="p-4 text-center">
              <p className="text-sm text-muted-foreground mb-2">
                Failed to load conversations
              </p>
              <Button
                onClick={refreshConversations}
                variant="outline"
                size="sm"
                aria-label="Retry loading conversations"
              >
                Retry
              </Button>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && conversations.length === 0 && (
            <div className="p-4 text-center">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                No conversations yet
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Click "New Chat" to start
              </p>
            </div>
          )}

          {/* Conversations list */}
          {!isLoading && !error && conversations.length > 0 && (
            <SidebarMenu>
              {conversations.map((conversation) => (
                <ConversationItem
                  key={conversation.threadId}
                  conversation={conversation}
                />
              ))}
            </SidebarMenu>
          )}
        </ScrollArea>
      </SidebarContent>
    </Sidebar>
  );
}
