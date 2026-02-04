'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { api, ChatMessage as ChatMessageType, Email, ChatResponse } from '@/lib/api';
import { cn } from '@/lib/utils';
import ChatMessage from './ChatMessage';
import LoadingDots from './LoadingDots';

interface ChatInterfaceProps {
  userName: string;
}

export default function ChatInterface({ userName }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentEmails, setCurrentEmails] = useState<Email[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Add welcome message on mount
    const welcomeMessage: ChatMessageType = {
      role: 'assistant',
      content: `Hello ${userName}! 👋 I'm your AI email assistant. I can help you manage your Gmail inbox.\n\nHere's what I can do:\n• **Show emails** - "Show my recent emails" or "Get my last 5 emails"\n• **Summarize emails** - I'll provide AI-generated summaries\n• **Reply to emails** - "Reply to email 1" or "Generate a reply for the email from John"\n• **Delete emails** - "Delete email 2" or "Delete the email about invoices"\n• **Daily digest** - "Give me today's email digest"\n\nJust type naturally and I'll help you out! What would you like to do?`,
      timestamp: new Date().toISOString(),
    };
    setMessages([welcomeMessage]);
  }, [userName]);

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessageType = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setError(null);
    setIsLoading(true);
    setStatusMessage('Processing your request...');

    try {
      // Build conversation history for context
      const history = messages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response: ChatResponse = await api.sendChatMessage(
        userMessage.content,
        history
      );

      // Handle response
      const assistantMessage: ChatMessageType = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
        metadata: {
          action: response.action,
          emails: response.data?.emails,
        },
      };

      // Update emails context if returned
      if (response.data?.emails) {
        setCurrentEmails(response.data.emails);
      }

      // Handle single email with suggested reply
      if (response.data?.email && response.data?.suggested_reply) {
        const emailWithReply = {
          ...response.data.email,
          suggested_reply: response.data.suggested_reply,
        };
        setCurrentEmails((prev) => {
          const updated = prev.map((e) =>
            e.id === emailWithReply.id ? emailWithReply : e
          );
          return updated;
        });
      }

      setMessages((prev) => [...prev, assistantMessage]);
      setStatusMessage(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Something went wrong';
      setError(errorMessage);
      
      const errorAssistantMessage: ChatMessageType = {
        role: 'assistant',
        content: `I encountered an error: ${errorMessage}\n\nPlease try again or rephrase your request.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorAssistantMessage]);
    } finally {
      setIsLoading(false);
      setStatusMessage(null);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleReplyEmail = (email: Email) => {
    const emailIndex = currentEmails.findIndex((e) => e.id === email.id) + 1;
    setInput(`Generate a reply for email ${emailIndex}`);
    inputRef.current?.focus();
  };

  const handleDeleteEmail = (email: Email) => {
    const emailIndex = currentEmails.findIndex((e) => e.id === email.id) + 1;
    setInput(`Delete email ${emailIndex}`);
    inputRef.current?.focus();
  };

  const quickActions = [
    { label: 'Show my emails', action: 'Show my last 5 emails' },
    { label: 'Daily digest', action: 'Give me today\'s email digest' },
    { label: 'Categorize inbox', action: 'Categorize my recent emails' },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <ChatMessage
            key={index}
            message={message}
            emails={message.metadata?.emails}
            onReplyEmail={handleReplyEmail}
            onDeleteEmail={handleDeleteEmail}
          />
        ))}
        
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
              <Loader2 className="w-4 h-4 animate-spin text-gray-600" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
              <div className="flex items-center gap-2">
                <LoadingDots />
                <span className="text-sm text-gray-500">{statusMessage}</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Quick actions */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2">
          <div className="flex flex-wrap gap-2">
            {quickActions.map((action, index) => (
              <button
                key={index}
                onClick={() => {
                  setInput(action.action);
                  inputRef.current?.focus();
                }}
                className="px-3 py-1.5 text-sm bg-primary-50 text-primary-700 rounded-full hover:bg-primary-100 transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mx-4 mb-2 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-500 hover:text-red-700"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="p-4 border-t border-gray-200 bg-white">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message... (e.g., 'Show my recent emails')"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || isLoading}
            className={cn(
              'px-4 py-3 rounded-xl font-medium transition-colors',
              input.trim() && !isLoading
                ? 'bg-primary-600 text-white hover:bg-primary-700'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            )}
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
