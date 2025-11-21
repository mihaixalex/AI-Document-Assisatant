'use client';

import React, { useState } from 'react';
import { Plus, Menu, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Card } from '@/components/ui/card';
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from '@/components/ui/drawer';
import { useIsMobile } from '@/components/ui/use-mobile';
import { useConversations } from '@/contexts/ConversationContext';
import { ConversationItem } from '@/components/conversation-item';
import { cn } from '@/lib/utils';

interface ConversationSidebarProps {
  className?: string;
}

function SidebarContent({ onItemClick }: { onItemClick?: () => void }) {
  const {
    conversations,
    currentThreadId,
    isLoading,
    error,
    setCurrentThreadId,
    createConversation,
    deleteConversation,
    refreshConversations,
  } = useConversations();

  const handleNewChat = async () => {
    const newConversation = await createConversation();
    if (newConversation) {
      setCurrentThreadId(newConversation.threadId);
    }
  };

  const handleSelectConversation = (threadId: string) => {
    setCurrentThreadId(threadId);
    onItemClick?.();
  };

  const handleDeleteConversation = async (threadId: string) => {
    await deleteConversation(threadId);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header with New Chat button */}
      <div className="p-4 border-b">
        <Button
          onClick={handleNewChat}
          className="w-full justify-start gap-2"
          variant="outline"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Conversations list */}
      <div
        className="flex-1 overflow-y-auto p-2"
        role="navigation"
        aria-label="Conversation history"
      >
        {isLoading ? (
          // Loading skeleton
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <Card key={i} className="p-3">
                <Skeleton className="h-4 w-3/4 mb-2" />
                <Skeleton className="h-3 w-1/2" />
              </Card>
            ))}
          </div>
        ) : error ? (
          // Error state
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-4">
            <AlertCircle className="h-12 w-12 text-destructive" />
            <div>
              <p className="text-sm font-medium text-foreground">
                Failed to load conversations
              </p>
              <p className="text-xs text-muted-foreground mt-1">{error}</p>
            </div>
            <Button onClick={refreshConversations} variant="outline" size="sm">
              Retry
            </Button>
          </div>
        ) : conversations.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <p className="text-sm text-muted-foreground">
              No conversations yet
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Start a new chat to begin
            </p>
          </div>
        ) : (
          // Conversations list with fade-in animation
          <div className="space-y-1 animate-in fade-in duration-300">
            {conversations.map((conversation) => (
              <ConversationItem
                key={conversation.threadId}
                conversation={conversation}
                isActive={conversation.threadId === currentThreadId}
                onClick={() => handleSelectConversation(conversation.threadId)}
                onDelete={handleDeleteConversation}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function ConversationSidebar({ className }: ConversationSidebarProps) {
  const isMobile = useIsMobile();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  if (isMobile) {
    // Mobile: Drawer with hamburger trigger
    return (
      <>
        {/* Hamburger menu trigger */}
        <div className="fixed top-4 left-4 z-50">
          <Drawer open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
            <DrawerTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="h-10 w-10"
                aria-label="Open conversation menu"
              >
                <Menu className="h-5 w-5" />
              </Button>
            </DrawerTrigger>
            <DrawerContent>
              <DrawerHeader>
                <DrawerTitle>Conversations</DrawerTitle>
              </DrawerHeader>
              <div className="h-[60vh] overflow-hidden">
                <SidebarContent onItemClick={() => setIsDrawerOpen(false)} />
              </div>
            </DrawerContent>
          </Drawer>
        </div>
      </>
    );
  }

  // Desktop: Fixed sidebar
  return (
    <aside
      className={cn(
        'fixed left-0 top-0 h-screen w-[280px] border-r bg-background z-40',
        className
      )}
    >
      <SidebarContent />
    </aside>
  );
}
