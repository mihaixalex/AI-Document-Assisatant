'use client';

import React, { useState, useCallback } from 'react';
import { useConversation } from '@/contexts/conversation-context';
import { MobileSidebar } from '@/components/conversation-sidebar';
import { Plus, Loader2, ChevronDown } from 'lucide-react';

// NEXUS Logo - Abstract network/nexus symbol
function NexusLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="currentColor"
      className={className}
      aria-label="Nexus Logo"
    >
      {/* Three interconnected nodes forming an abstract nexus */}
      {/* Top node */}
      <circle cx="20" cy="8" r="3"/>
      {/* Bottom left node */}
      <circle cx="8" cy="32" r="3"/>
      {/* Bottom right node */}
      <circle cx="32" cy="32" r="3"/>

      {/* Connecting lines (network edges) */}
      <path d="M20 11 L10 29" stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none"/>
      <path d="M20 11 L30 29" stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none"/>
      <path d="M11 32 L29 32" stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none"/>

      {/* Center nexus point */}
      <circle cx="20" cy="24" r="4"/>
    </svg>
  );
}

// AI Avatar component for chat messages
export function AIAvatar({ className }: { className?: string }) {
  return (
    <div className={`w-8 h-8 rounded-full bg-white flex items-center justify-center shrink-0 ${className || ''}`}>
      <NexusLogo className="w-5 h-5 text-black" />
    </div>
  );
}

export function ConversationHeader() {
  const { conversations, currentThreadId, createConversation } = useConversation();
  const [isCreating, setIsCreating] = useState(false);
  const [selectedModel, setSelectedModel] = useState('GPT-4o');

  const currentConversation = conversations.find(
    (c) => c.threadId === currentThreadId
  );

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
    <header className="h-16 border-b border-[#1F1F1F] flex items-center px-4 bg-black">
      {/* Left side - Mobile menu + Logo */}
      <div className="flex items-center gap-3">
        {/* Mobile hamburger menu */}
        <MobileSidebar />

        {/* Logo - visible on all screens */}
        <div className="flex items-center gap-2">
          <NexusLogo className="h-7 w-7 text-white" />
          <span className="hidden sm:block font-semibold text-white tracking-wider">NEXUS</span>
        </div>
      </div>

      {/* Center - Spacer */}
      <div className="flex-1" />

      {/* Right side - Actions */}
      <div className="flex items-center gap-2">
        {/* New Chat button - Desktop only */}
        <button
          onClick={handleNewChat}
          disabled={isCreating}
          className="hidden md:flex px-4 py-2 bg-[#1F1F1F] hover:bg-[#2F2F2F] rounded-full text-white font-medium items-center gap-2 transition-colors disabled:opacity-50"
          aria-label="New conversation"
        >
          {isCreating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
          <span>New Chat</span>
        </button>

        {/* Model selector */}
        <div className="relative">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="appearance-none bg-[#1F1F1F] border border-[#1F1F1F] hover:bg-[#2F2F2F] rounded-md px-3 py-2 pr-8 text-white text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#00FF9D]"
            aria-label="Select model"
          >
            <option value="GPT-4o">GPT-4o</option>
            <option value="GPT-4o-mini">GPT-4o Mini</option>
            <option value="Claude-3.5">Claude 3.5</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-[#AAAAAA] pointer-events-none" />
        </div>

        {/* User avatar */}
        <div className="w-8 h-8 rounded-full bg-[#00FF9D] flex items-center justify-center text-black font-medium text-sm">
          U
        </div>
      </div>
    </header>
  );
}
