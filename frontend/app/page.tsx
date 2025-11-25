'use client';

import type React from 'react';

import { useToast } from '@/hooks/use-toast';
import { useRef, useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Paperclip, ArrowUp, Loader2 } from 'lucide-react';
import { ExamplePrompts } from '@/components/example-prompts';
import { ChatMessage } from '@/components/chat-message';
import { FilePreview } from '@/components/file-preview';
import {
  AgentState,
  documentType,
  PDFDocument,
} from '@/types/graphTypes';
import Particles from '@/components/particles';
import { ThemeToggle } from '@/components/theme-toggle';
import { useTheme } from 'next-themes';
import { useConversation } from '@/contexts/conversation-context';
import { ConversationSidebar } from '@/components/conversation-sidebar';
import { ConversationHeader } from '@/components/conversation-header';
import { SidebarInset } from '@/components/ui/sidebar';

// Type definitions for backend messages
interface BackendMessage {
  type: 'human' | 'ai';
  content: string;
  sources?: PDFDocument[];
}

interface SSEEvent {
  event: string;
  data: unknown;
}

interface NodeUpdate {
  [key: string]: {
    messages?: BackendMessage[];
    documents?: PDFDocument[];
  };
}

export default function Home() {
  const { resolvedTheme } = useTheme();
  const isDarkMode = resolvedTheme === 'dark';
  const { toast } = useToast();
  const { currentThreadId } = useConversation();

  const [messages, setMessages] = useState<
    Array<{
      role: 'user' | 'assistant';
      content: string;
      sources?: PDFDocument[];
    }>
  >([]);
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadToShared, setUploadToShared] = useState(false); // Shared knowledge base toggle
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastRetrievedDocsRef = useRef<PDFDocument[]>([]);

  // Load conversation history when currentThreadId changes
  useEffect(() => {
    if (!currentThreadId) return;

    const loadHistory = async () => {
      try {
        const response = await fetch(`/api/conversations/${currentThreadId}/history`);
        if (!response.ok) {
          throw new Error('Failed to load conversation history');
        }
        const data = await response.json();

        // Transform backend messages to frontend format
        if (data.messages && Array.isArray(data.messages)) {
          const formattedMessages = data.messages.map((msg: BackendMessage) => ({
            role: msg.type === 'human' ? ('user' as const) : ('assistant' as const),
            content: msg.content,
            sources: msg.sources || undefined,
          }));
          setMessages(formattedMessages);
        } else {
          // No history, start fresh
          setMessages([]);
        }
      } catch (error) {
        console.error('Error loading conversation history:', error);
        // Start with empty messages on error
        setMessages([]);
      }
    };

    loadHistory();
  }, [currentThreadId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !currentThreadId || isLoading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const userMessage = input.trim();
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, sources: undefined }, // Clear sources for new user message
      { role: 'assistant', content: '', sources: undefined }, // Clear sources for new assistant message
    ]);
    setInput('');
    setIsLoading(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    lastRetrievedDocsRef.current = []; // Clear the last retrieved documents

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          threadId: currentThreadId,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunkStr = decoder.decode(value);
        const lines = chunkStr.split('\n').filter(Boolean);

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;

          const sseString = line.slice('data: '.length);
          let sseEvent: SSEEvent;
          try {
            sseEvent = JSON.parse(sseString) as SSEEvent;
          } catch (err) {
            console.error('Error parsing SSE line:', err, line);
            continue;
          }

          const { event, data } = sseEvent;

          if (event === 'messages/partial') {
            if (Array.isArray(data)) {
              const lastObj = data[data.length - 1] as BackendMessage | undefined;
              if (lastObj?.type === 'ai') {
                const partialContent = lastObj.content ?? '';

                // Only display if content is a string message
                if (
                  typeof partialContent === 'string' &&
                  !partialContent.startsWith('{')
                ) {
                  setMessages((prev) => {
                    const newArr = [...prev];
                    if (
                      newArr.length > 0 &&
                      newArr[newArr.length - 1].role === 'assistant'
                    ) {
                      newArr[newArr.length - 1].content = partialContent;
                      newArr[newArr.length - 1].sources =
                        lastRetrievedDocsRef.current;
                    }

                    return newArr;
                  });
                }
              }
            }
          } else if (event === 'updates' && data) {
            // Extract the updates object (backend sends data.updates.nodeName)
            const dataObj = data as { updates?: NodeUpdate } | NodeUpdate;
            const updates = ('updates' in dataObj ? dataObj.updates : dataObj) as NodeUpdate;

            // Handle document retrieval updates
            if (
              updates?.retrieveDocuments?.documents &&
              Array.isArray(updates.retrieveDocuments.documents)
            ) {
              const retrievedDocs = updates.retrieveDocuments.documents as PDFDocument[];
              lastRetrievedDocsRef.current = retrievedDocs;
              console.log('Retrieved documents:', retrievedDocs);
            }

            // Handle directAnswer node - extract AI message
            if (
              updates?.directAnswer?.messages &&
              Array.isArray(updates.directAnswer.messages)
            ) {
              const messages = updates.directAnswer.messages;
              const aiMessage = messages.find((msg: BackendMessage) => msg.type === 'ai');

              if (aiMessage && typeof aiMessage.content === 'string') {
                setMessages((prev) => {
                  const newArr = [...prev];
                  if (
                    newArr.length > 0 &&
                    newArr[newArr.length - 1].role === 'assistant'
                  ) {
                    newArr[newArr.length - 1].content = aiMessage.content;
                    newArr[newArr.length - 1].sources =
                      lastRetrievedDocsRef.current;
                  }
                  return newArr;
                });
              }
            }

            // Handle generateResponse node - extract AI message
            if (
              updates?.generateResponse?.messages &&
              Array.isArray(updates.generateResponse.messages)
            ) {
              const messages = updates.generateResponse.messages;
              const aiMessage = messages.find((msg: BackendMessage) => msg.type === 'ai');

              if (aiMessage && typeof aiMessage.content === 'string') {
                setMessages((prev) => {
                  const newArr = [...prev];
                  if (
                    newArr.length > 0 &&
                    newArr[newArr.length - 1].role === 'assistant'
                  ) {
                    newArr[newArr.length - 1].content = aiMessage.content;
                    newArr[newArr.length - 1].sources =
                      lastRetrievedDocsRef.current;
                  }
                  return newArr;
                });
              }
            }
          } else {
            console.log('Unknown SSE event:', event, data);
          }
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      toast({
        title: 'Error',
        description:
          'Failed to send message. Please try again.\n' +
          (error instanceof Error ? error.message : 'Unknown error'),
        variant: 'destructive',
      });
      setMessages((prev) => {
        const newArr = [...prev];
        newArr[newArr.length - 1].content =
          'Sorry, there was an error processing your message.';
        return newArr;
      });
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length === 0) return;

    if (!currentThreadId) {
      toast({
        title: 'Error',
        description: 'No active conversation. Please create a conversation first.',
        variant: 'destructive',
      });
      return;
    }

    const nonPdfFiles = selectedFiles.filter(
      (file) => file.type !== 'application/pdf',
    );
    if (nonPdfFiles.length > 0) {
      toast({
        title: 'Invalid file type',
        description: 'Please upload PDF files only',
        variant: 'destructive',
      });
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      selectedFiles.forEach((file) => {
        formData.append('files', file);
      });
      formData.append('threadId', currentThreadId);
      formData.append('isShared', uploadToShared.toString()); // Pass shared KB flag

      const response = await fetch('/api/ingest', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to upload files');
      }

      setFiles((prev) => [...prev, ...selectedFiles]);
      toast({
        title: 'Success',
        description: `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} uploaded successfully`,
        variant: 'default',
      });
    } catch (error) {
      console.error('Error uploading files:', error);
      toast({
        title: 'Upload failed',
        description:
          'Failed to upload files. Please try again.\n' +
          (error instanceof Error ? error.message : 'Unknown error'),
        variant: 'destructive',
      });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemoveFile = (fileToRemove: File) => {
    setFiles(files.filter((file) => file !== fileToRemove));
    toast({
      title: 'File removed',
      description: `${fileToRemove.name} has been removed`,
      variant: 'default',
    });
  };

  return (
    <>
      <ConversationSidebar />
      <SidebarInset>
        {/* Particles background - only visible in dark mode */}
        {isDarkMode && (
          <div className="fixed inset-0 pointer-events-none z-0">
            <Particles
              particleCount={150}
              particleSpread={15}
              speed={0.05}
              particleColors={['#ffffff', '#ffffff', '#ffffff']}
              alphaParticles={true}
              particleBaseSize={200}
              sizeRandomness={2}
            />
          </div>
        )}

        {/* Theme toggle button */}
        <ThemeToggle />

        {/* Header with conversation title and mobile menu */}
        <ConversationHeader />

        <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center p-4 md:p-24 max-w-5xl mx-auto w-full relative z-10">
          {messages.length === 0 ? (
          <>
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <p className="font-medium text-muted-foreground max-w-md mx-auto text-2xl">
                  Coffee and Jarvis time? ☕
                </p>
              </div>
            </div>
            <ExamplePrompts onPromptSelect={setInput} />
          </>
        ) : (
          <div className="w-full space-y-4 mb-20">
            {messages.map((message, i) => (
              <ChatMessage key={i} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}

        <div className="fixed bottom-0 left-0 right-0 p-4 bg-background md:left-[var(--sidebar-width)]">
          <div className="max-w-5xl mx-auto space-y-4">
          {files.length > 0 && (
            <div className="grid grid-cols-3 gap-2">
              {files.map((file, index) => (
                <FilePreview
                  key={`${file.name}-${index}`}
                  file={file}
                  onRemove={() => handleRemoveFile(file)}
                />
              ))}
            </div>
          )}

          {/* Shared knowledge base toggle */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="shared-kb"
              checked={uploadToShared}
              onCheckedChange={(checked) => setUploadToShared(checked === true)}
            />
            <Label htmlFor="shared-kb" className="text-sm text-muted-foreground cursor-pointer">
              Add to shared knowledge base (accessible in all conversations)
            </Label>
          </div>

          <form onSubmit={handleSubmit} className="relative">
            <div
              className="flex gap-2 border rounded-md overflow-hidden shadow-sm transition-colors"
              style={{
                backgroundColor: isDarkMode ? '#111827' : '#ffffff',
                borderColor: isDarkMode ? '#1f2937' : '#e5e7eb',
              }}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".pdf"
                multiple
                className="hidden"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="rounded-none h-12"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                style={{
                  backgroundColor: 'transparent',
                  color: isDarkMode ? '#f9fafb' : '#111827',
                }}
              >
                {isUploading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-foreground" />
                  </div>
                ) : (
                  <Paperclip className="h-4 w-4 text-foreground" />
                )}
              </Button>
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  isUploading ? 'Uploading PDF...' : 'Send a message...'
                }
                className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0 h-12 bg-transparent"
                disabled={isUploading || isLoading || !currentThreadId}
                style={{
                  backgroundColor: 'transparent',
                  color: isDarkMode ? '#f9fafb' : '#111827',
                }}
              />
              <Button
                type="submit"
                variant="ghost"
                size="icon"
                className="rounded-none h-12"
                disabled={
                  !input.trim() || isUploading || isLoading || !currentThreadId
                }
                style={{
                  backgroundColor: 'transparent',
                  color: isDarkMode ? '#f9fafb' : '#111827',
                }}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ArrowUp className="h-4 w-4" />
                )}
              </Button>
            </div>
          </form>
          </div>
        </div>
      </main>
      </SidebarInset>
    </>
  );
}
