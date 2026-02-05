'use client';

import { Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage as ChatMessageType, Email } from '@/lib/api';
import { cn } from '@/lib/utils';
import EmailCard from './EmailCard';

interface ChatMessageProps {
  message: ChatMessageType;
  emails?: Email[];
  onReplyEmail?: (email: Email) => void;
  onDeleteEmail?: (email: Email) => void;
}

function cleanMessageContent(content: string, hasEmails: boolean = false): string {
  let cleaned = content
    .replace(/```json[\s\S]*?```/g, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/\{[^{}]*"action"[^{}]*\}/g, '')
    .replace(/To read these emails, I can use the following action:/gi, '')
    .replace(/I can use the following action:/gi, '')
    .trim();
  
  if (hasEmails) {
    cleaned = cleaned
      .replace(/Here are your last \d+ emails.*?:/gi, '')
      .replace(/I'll fetch your recent emails\..*$/gim, '')
      .replace(/^\d+\.\s+\*\*Email from.*$/gim, '')
      .replace(/^\d+\.\s+\*\*Newsletter from.*$/gim, '')
      .replace(/^-\s+\*\*Email from.*$/gim, '')
      .replace(/Here are your.*emails.*summary:?/gi, '')
      .replace(/I'll fetch your recent emails\. Here are your last \d+ emails with a brief summary:/gi, '');
    
    const lines = cleaned.split('\n');
    const filteredLines = lines.filter(line => {
      const trimmed = line.trim();
      if (/^\d+\.\s+\*\*/.test(trimmed) && /\(sent.*ago\)/.test(trimmed)) return false;
      if (/^Email \d+:/.test(trimmed)) return false;
      return true;
    });
    cleaned = filteredLines.join('\n');
  }
  
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();
  
  if (hasEmails && cleaned.length < 20) {
    cleaned = "Here are your recent emails:";
  }
  
  return cleaned;
}

export default function ChatMessage({
  message,
  emails,
  onReplyEmail,
  onDeleteEmail,
}: ChatMessageProps) {
  const isUser = message.role === 'user';
  const hasEmails = emails && emails.length > 0;
  const displayContent = isUser ? message.content : cleanMessageContent(message.content, hasEmails);

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
          {isUser ? (
            <p className="whitespace-pre-wrap">{displayContent}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-strong:text-gray-900">
              <ReactMarkdown>{displayContent}</ReactMarkdown>
            </div>
          )}
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
