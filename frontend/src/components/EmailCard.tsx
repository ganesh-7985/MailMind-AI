'use client';

import { Mail, Clock, User, Reply, Trash2 } from 'lucide-react';
import { Email } from '@/lib/api';
import { formatDate, truncateText } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface EmailCardProps {
  email: Email;
  index: number;
  onReply?: (email: Email) => void;
  onDelete?: (email: Email) => void;
  compact?: boolean;
}

export default function EmailCard({
  email,
  index,
  onReply,
  onDelete,
  compact = false,
}: EmailCardProps) {
  return (
    <div
      className={cn(
        'bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow',
        compact && 'p-3'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="flex-shrink-0 w-8 h-8 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-sm font-medium">
            {index}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <User className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <span className="font-medium text-gray-900 truncate">
                {email.sender}
              </span>
              <span className="text-gray-400 text-sm truncate hidden sm:inline">
                &lt;{email.sender_email}&gt;
              </span>
            </div>
            <h3 className="font-semibold text-gray-800 mb-1 truncate">
              {email.subject}
            </h3>
            {email.summary && (
              <p className="text-sm text-gray-600 mb-2">
                <span className="font-medium text-primary-600">Summary: </span>
                {truncateText(email.summary, compact ? 100 : 200)}
              </p>
            )}
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              <span>{formatDate(email.date)}</span>
            </div>
          </div>
        </div>
        
        {(onReply || onDelete) && (
          <div className="flex items-center gap-2 flex-shrink-0">
            {onReply && (
              <button
                onClick={() => onReply(email)}
                className="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                title="Reply"
              >
                <Reply className="w-4 h-4" />
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => onDelete(email)}
                className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>
      
      {email.suggested_reply && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-sm font-medium text-green-700 mb-1">Suggested Reply:</p>
          <p className="text-sm text-gray-700 bg-green-50 p-3 rounded-lg">
            {truncateText(email.suggested_reply, 300)}
          </p>
        </div>
      )}
    </div>
  );
}
