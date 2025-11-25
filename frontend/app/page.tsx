'use client';

import type React from 'react';

import { useToast } from '@/hooks/use-toast';
import { useRef, useState, useEffect } from 'react';
import { Paperclip, ArrowUp, Loader2 } from 'lucide-react';
import { ChatMessage } from '@/components/chat-message';
import { FilePreview } from '@/components/file-preview';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  PDFDocument,
} from '@/types/graphTypes';
import { useConversation } from '@/contexts/conversation-context';
import { ConversationSidebar } from '@/components/conversation-sidebar';
import { ConversationHeader } from '@/components/conversation-header';

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
  const [uploadToShared, setUploadToShared] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastRetrievedDocsRef = useRef<PDFDocument[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

        if (data.messages && Array.isArray(data.messages)) {
          const formattedMessages = data.messages.map((msg: BackendMessage) => ({
            role: msg.type === 'human' ? ('user' as const) : ('assistant' as const),
            content: msg.content,
            sources: msg.sources || undefined,
          }));
          setMessages(formattedMessages);
        } else {
          setMessages([]);
        }
      } catch (error) {
        console.error('Error loading conversation history:', error);
        setMessages([]);
      }
    };

    loadHistory();
  }, [currentThreadId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 192)}px`;
    }
  }, [input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !currentThreadId || isLoading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const userMessage = input.trim();
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, sources: undefined },
      { role: 'assistant', content: '', sources: undefined },
    ]);
    setInput('');
    setIsLoading(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    lastRetrievedDocsRef.current = [];

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
      let buffer = ''; // Buffer for incomplete SSE lines

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Append new data to buffer and process complete lines
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        // Keep the last incomplete line in buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue;

          const sseString = trimmedLine.slice('data: '.length);
          let sseEvent: SSEEvent;
          try {
            sseEvent = JSON.parse(sseString) as SSEEvent;
          } catch (err) {
            console.error('Error parsing SSE line:', err, trimmedLine);
            continue;
          }

          const { event, data } = sseEvent;

          if (event === 'messages/partial') {
            if (Array.isArray(data)) {
              const lastObj = data[data.length - 1] as BackendMessage | undefined;
              if (lastObj?.type === 'ai') {
                const partialContent = lastObj.content ?? '';

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
                      // Create new object to ensure React detects the change
                      newArr[newArr.length - 1] = {
                        ...newArr[newArr.length - 1],
                        content: partialContent,
                        sources: lastRetrievedDocsRef.current,
                      };
                    }

                    return newArr;
                  });
                }
              }
            }
          } else if (event === 'updates' && data) {
            const updates = data as NodeUpdate;

            // Handle document retrieval
            if (
              updates?.retrieveDocuments?.documents &&
              Array.isArray(updates.retrieveDocuments.documents)
            ) {
              lastRetrievedDocsRef.current = updates.retrieveDocuments.documents as PDFDocument[];
            }

            // Handle direct answer
            if (
              updates?.directAnswer?.messages &&
              Array.isArray(updates.directAnswer.messages)
            ) {
              const aiMessage = updates.directAnswer.messages.find(
                (msg: BackendMessage) => msg.type === 'ai'
              );

              if (aiMessage && typeof aiMessage.content === 'string') {
                setMessages((prev) => {
                  const newArr = [...prev];
                  if (
                    newArr.length > 0 &&
                    newArr[newArr.length - 1].role === 'assistant'
                  ) {
                    // Create new object to ensure React detects the change
                    newArr[newArr.length - 1] = {
                      ...newArr[newArr.length - 1],
                      content: aiMessage.content,
                      sources: lastRetrievedDocsRef.current,
                    };
                  }
                  return newArr;
                });
              }
            }

            // Handle generate response
            if (
              updates?.generateResponse?.messages &&
              Array.isArray(updates.generateResponse.messages)
            ) {
              const aiMessage = updates.generateResponse.messages.find(
                (msg: BackendMessage) => msg.type === 'ai'
              );

              if (aiMessage && typeof aiMessage.content === 'string') {
                setMessages((prev) => {
                  const newArr = [...prev];
                  if (
                    newArr.length > 0 &&
                    newArr[newArr.length - 1].role === 'assistant'
                  ) {
                    // Create new object to ensure React detects the change
                    newArr[newArr.length - 1] = {
                      ...newArr[newArr.length - 1],
                      content: aiMessage.content,
                      sources: lastRetrievedDocsRef.current,
                    };
                  }
                  return newArr;
                });
              }
            }
          } else if (event === 'error') {
            console.error('SSE error event:', data);
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
        if (newArr.length > 0 && newArr[newArr.length - 1].role === 'assistant') {
          // Create new object to ensure React detects the change
          newArr[newArr.length - 1] = {
            ...newArr[newArr.length - 1],
            content: 'Sorry, there was an error processing your message.',
          };
        }
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
      formData.append('isShared', uploadToShared.toString());

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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <>
      {/* Desktop Sidebar */}
      <ConversationSidebar />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col bg-black min-w-0">
        {/* Header */}
        <ConversationHeader />

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto w-full px-4 py-4">
            {messages.length === 0 ? (
              /* Empty State */
              <div className="flex flex-col items-center justify-center h-[calc(100vh-12rem)] text-[#AAAAAA]">
                <h1 className="text-2xl font-semibold mb-2 text-white">What do you want to know?</h1>
                <p className="text-sm">Ask me anything about your documents.</p>
              </div>
            ) : (
              /* Messages */
              <div className="flex flex-col space-y-4 pb-32">
                {messages.map((message, i) => (
                  <ChatMessage key={i} message={message} />
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Input Bar (Footer) */}
        <footer className="border-t border-[#1F1F1F] p-4 bg-black">
          <div className="max-w-4xl mx-auto">
            {/* File Previews */}
            {files.length > 0 && (
              <div className="grid grid-cols-3 gap-2 mb-3">
                {files.map((file, index) => (
                  <FilePreview
                    key={`${file.name}-${index}`}
                    file={file}
                    onRemove={() => handleRemoveFile(file)}
                  />
                ))}
              </div>
            )}

            {/* Shared KB Toggle */}
            <div className="flex items-center gap-3 mb-3">
              <Switch
                id="shared-kb"
                checked={uploadToShared}
                onCheckedChange={setUploadToShared}
                className="data-[state=checked]:bg-[#00FF9D] data-[state=unchecked]:bg-[#333333]"
              />
              <Label
                htmlFor="shared-kb"
                className="text-sm text-[#AAAAAA] cursor-pointer hover:text-white transition-colors"
              >
                Add to shared knowledge base
              </Label>
            </div>

            {/* Input Form */}
            <form onSubmit={handleSubmit}>
              <div className="flex items-end gap-2">
                {/* Upload Button */}
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".pdf"
                  multiple
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  className="w-10 h-10 flex items-center justify-center text-[#AAAAAA] hover:text-[#00FF9D] transition-colors disabled:opacity-50 shrink-0"
                  aria-label="Upload file"
                >
                  {isUploading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Paperclip className="h-5 w-5" />
                  )}
                </button>

                {/* Textarea */}
                <div className="flex-1 relative">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={isUploading ? 'Uploading PDF...' : 'Send a message...'}
                    disabled={isUploading || isLoading || !currentThreadId}
                    className="w-full bg-[#1F1F1F] border border-[#333333] rounded-2xl p-4 pr-12 text-white placeholder-[#666666] resize-none focus:outline-none focus:border-[#00FF9D] transition-colors disabled:opacity-50 max-h-48"
                    rows={1}
                  />
                </div>

                {/* Send Button */}
                <button
                  type="submit"
                  disabled={!input.trim() || isUploading || isLoading || !currentThreadId}
                  className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors shrink-0 ${
                    input.trim() && !isLoading
                      ? 'bg-[#00FF9D] text-black hover:bg-[#00E08A]'
                      : 'bg-[#333333] text-[#666666]'
                  } disabled:cursor-not-allowed`}
                  aria-label="Send message"
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <ArrowUp className="h-5 w-5" />
                  )}
                </button>
              </div>
            </form>
          </div>
        </footer>
      </main>
    </>
  );
}
