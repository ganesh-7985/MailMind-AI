'use client';

import { Bot, User } from 'lucide-react';
import { ChatMessage as ChatMessageType, Email } from '@/lib/api';
import { cn } from '@/lib/utils';
import EmailCard from './EmailCard';

interface ChatMessageProps {
  message: ChatMessageType;
  emails?: Email[];
  onReplyEmail?: (email: Email) => void;
  onDeleteEmail?: (email: Email) => void;
}

export default function ChatMessage({
  message,
  emails,
  onReplyEmail,
  onDeleteEmail,
}: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 message-enter',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      
      <div
        className={cn(
          'flex-1 max-w-[85%]',
          isUser ? 'text-right' : 'text-left'
        )}
      >
        <div
          className={cn(
            'inline-block rounded-2xl px-4 py-2 text-sm',
            isUser
              ? 'bg-primary-600 text-white rounded-br-md'
              : 'bg-white text-gray-800 border border-gray-200 rounded-bl-md shadow-sm'
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        
        {/* Show emails if available */}
        {emails && emails.length > 0 && (
          <div className="mt-3 space-y-2">
            {emails.map((email, index) => (
              <EmailCard
                key={email.id}
                email={email}
                index={index + 1}
                onReply={onReplyEmail}
                onDelete={onDeleteEmail}
                compact
              />
            ))}
          </div>
        )}
        
        {message.timestamp && (
          <p className="text-xs text-gray-400 mt-1">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        )}
      </div>
    </div>
  );
}
