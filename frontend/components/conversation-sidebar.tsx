'use client';

import React, { useState, useCallback } from 'react';
import { Plus, MessageSquare, Loader2, Menu } from 'lucide-react';
import { useConversation } from '@/contexts/conversation-context';
import { ConversationItem } from '@/components/conversation-item';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Drawer,
  DrawerContent,
  DrawerTrigger,
} from '@/components/ui/drawer';

interface SidebarContentProps {
  onNewChat: () => void;
  isCreating: boolean;
}

function SidebarContentInner({ onNewChat, isCreating }: SidebarContentProps) {
  const { conversations, isLoading, error, refreshConversations } = useConversation();

  const showLoading = isLoading && conversations.length === 0;
  const showError = error && !isLoading;
  const showEmpty = !isLoading && !error && conversations.length === 0;
  const showList = !isLoading && !error && conversations.length > 0;

  return (
    <>
      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          disabled={isCreating}
          className="w-full h-12 bg-[#1F1F1F] hover:bg-[#2F2F2F] rounded-md text-white font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          aria-label="New conversation"
        >
          {isCreating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
          <span>{isCreating ? 'Creating...' : 'New Chat'}</span>
        </button>
      </div>

      {/* Conversations List */}
      <div className="overflow-y-auto h-[calc(100vh-5rem)] px-2">
        {/* Loading state */}
        {showLoading && (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-2 p-3 rounded-md">
                <Skeleton className="h-4 w-4 rounded bg-[#333333]" />
                <div className="flex-1 space-y-1">
                  <Skeleton className="h-4 w-full bg-[#333333]" />
                  <Skeleton className="h-3 w-20 bg-[#333333]" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error state */}
        {showError && (
          <div className="p-4 text-center">
            <p className="text-sm text-[#AAAAAA] mb-2">Failed to load</p>
            <Button
              onClick={refreshConversations}
              variant="outline"
              size="sm"
              className="bg-[#1F1F1F] border-[#1F1F1F] hover:bg-[#2F2F2F] text-white"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty state */}
        {showEmpty && (
          <div className="p-6 text-center text-[#AAAAAA]">
            <MessageSquare className="h-8 w-8 mx-auto mb-2" />
            <p className="text-sm">No conversations yet.</p>
            <p className="text-xs mt-1">Start a new chat.</p>
          </div>
        )}

        {/* Conversations list */}
        {showList && (
          <div className="space-y-1" role="list" aria-label="Conversations">
            {conversations.map((conversation) => (
              <ConversationItem
                key={conversation.threadId}
                conversation={conversation}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

// Mobile Drawer Sidebar
export function MobileSidebar() {
  const { createConversation } = useConversation();
  const [isCreating, setIsCreating] = useState(false);
  const [open, setOpen] = useState(false);

  const handleNewChat = useCallback(async () => {
    if (isCreating) return;
    setIsCreating(true);
    try {
      await createConversation('New Conversation');
      setOpen(false);
    } catch (error) {
      console.error('Error creating conversation:', error);
    } finally {
      setIsCreating(false);
    }
  }, [isCreating, createConversation]);

  return (
    <Drawer direction="left" open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>
        <button
          className="md:hidden w-10 h-10 flex items-center justify-center text-white hover:bg-[#1F1F1F] rounded-md transition-colors"
          aria-label="Open menu"
        >
          <Menu className="w-6 h-6" />
        </button>
      </DrawerTrigger>
      <DrawerContent className="h-full w-[280px] bg-black border-r border-[#1F1F1F] rounded-none">
        <SidebarContentInner onNewChat={handleNewChat} isCreating={isCreating} />
      </DrawerContent>
    </Drawer>
  );
}

// Desktop Sidebar
export function ConversationSidebar() {
  const { createConversation } = useConversation();
  const [isCreating, setIsCreating] = useState(false);

  const handleNewChat = useCallback(async () => {
    if (isCreating) return;
    setIsCreating(true);
    try {
      await createConversation('New Conversation');
    } catch (error) {
      console.error('Error creating conversation:', error);
    } finally {
      setIsCreating(false);
    }
  }, [isCreating, createConversation]);

  return (
    <aside className="w-[280px] border-r border-[#1F1F1F] bg-black hidden md:block flex-shrink-0">
      <SidebarContentInner onNewChat={handleNewChat} isCreating={isCreating} />
    </aside>
  );
}
