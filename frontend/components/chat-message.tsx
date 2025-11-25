'use client';

import { Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { PDFDocument } from '@/types/graphTypes';
import { AIAvatar } from '@/components/conversation-header';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

interface ChatMessageProps {
  message: {
    role: 'user' | 'assistant';
    content: string;
    sources?: PDFDocument[];
  };
}

// Typing indicator component
function TypingIndicator() {
  return (
    <div className="flex space-x-1 h-6 items-center px-1">
      <div className="w-2 h-2 bg-[#AAAAAA] rounded-full animate-typing-dot" />
      <div className="w-2 h-2 bg-[#AAAAAA] rounded-full animate-typing-dot" />
      <div className="w-2 h-2 bg-[#AAAAAA] rounded-full animate-typing-dot" />
    </div>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const isLoading = message.role === 'assistant' && message.content === '';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const showSources =
    message.role === 'assistant' &&
    message.sources &&
    message.sources.length > 0;

  // User message - right aligned, green background
  if (isUser) {
    return (
      <div className="flex justify-end animate-message-in">
        <div className="bg-[#00FF9D] text-black rounded-l-2xl rounded-tr-2xl rounded-br-sm p-4 max-w-[80%]">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  // Assistant message - left aligned, gray background with avatar
  return (
    <div className="flex items-start gap-3 max-w-[80%] animate-message-in">
      <AIAvatar />
      <div className="flex-1 min-w-0">
        <div className="bg-[#1F1F1F] text-white rounded-r-2xl rounded-tl-sm rounded-bl-2xl p-4">
          {isLoading ? (
            <TypingIndicator />
          ) : (
            <>
              <p className="whitespace-pre-wrap">{message.content}</p>

              {/* Copy button */}
              <div className="flex gap-2 mt-3 pt-2 border-t border-[#333333]">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 text-xs text-[#AAAAAA] hover:text-white transition-colors"
                  title={copied ? 'Copied!' : 'Copy to clipboard'}
                  aria-label={copied ? 'Copied!' : 'Copy to clipboard'}
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-[#00FF9D]" />
                      <span className="text-[#00FF9D]">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>

              {/* Sources accordion */}
              {showSources && message.sources && (
                <Accordion type="single" collapsible className="w-full mt-3">
                  <AccordionItem value="sources" className="border-[#333333]">
                    <AccordionTrigger className="text-sm py-2 text-[#AAAAAA] hover:text-white hover:no-underline">
                      View Sources ({message.sources.length})
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {message.sources.map((source, index) => (
                          <div
                            key={index}
                            className="bg-[#0D0D0D] border border-[#333333] rounded-lg p-3 hover:bg-[#1A1A1A] transition-colors cursor-pointer"
                          >
                            <p className="text-sm font-medium text-white truncate">
                              {source.metadata?.source ||
                                source.metadata?.filename ||
                                'Unknown source'}
                            </p>
                            <p className="text-xs text-[#666666] mt-1">
                              Page {source.metadata?.loc?.pageNumber || 'N/A'}
                            </p>
                          </div>
                        ))}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
