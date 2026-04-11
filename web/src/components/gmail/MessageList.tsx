import type { ParsedGmailMessage } from '../../types/google.ts';

interface MessageListProps {
  messages: ParsedGmailMessage[];
  onSelect: (messageId: string) => void;
  onLoadMore?: () => void;
  hasMore: boolean;
  loading: boolean;
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    if (isToday) {
      return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function formatFrom(from: string): string {
  // "Name <email>" → "Name"
  const match = from.match(/^(.+?)\s*<.*>$/);
  return match ? match[1].replace(/"/g, '') : from;
}

export default function MessageList({ messages, onSelect, onLoadMore, hasMore, loading }: MessageListProps) {
  if (!loading && messages.length === 0) {
    return <div className="empty-state">받은 메일이 없습니다.</div>;
  }

  return (
    <div className="message-list">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`message-item ${msg.isUnread ? 'unread' : ''}`}
          onClick={() => onSelect(msg.id)}
        >
          <div className="message-from">{formatFrom(msg.from)}</div>
          <div className="message-subject">{msg.subject || '(제목 없음)'}</div>
          <div className="message-snippet">{msg.snippet}</div>
          <div className="message-date">{formatDate(msg.date)}</div>
        </div>
      ))}
      {hasMore && (
        <button
          className="load-more-btn"
          onClick={onLoadMore}
          disabled={loading}
        >
          {loading ? '로딩 중...' : '더 보기'}
        </button>
      )}
    </div>
  );
}
