import { ArrowLeft } from 'lucide-react';
import type { ParsedGmailMessage } from '../../types/google.ts';

interface MessageDetailProps {
  message: ParsedGmailMessage;
  onBack: () => void;
}

export default function MessageDetail({ message, onBack }: MessageDetailProps) {
  const isHtml = message.body.includes('<') && message.body.includes('>');

  return (
    <div className="message-detail">
      <button className="back-btn" onClick={onBack}>
        <ArrowLeft size={16} />
        <span>목록으로</span>
      </button>

      <div className="message-detail-header">
        <h3 className="message-detail-subject">{message.subject || '(제목 없음)'}</h3>
        <div className="message-detail-meta">
          <span className="message-detail-from">{message.from}</span>
          <span className="message-detail-date">{message.date}</span>
        </div>
        <div className="message-detail-to">받는 사람: {message.to}</div>
      </div>

      <div className="message-detail-body">
        {isHtml ? (
          <div dangerouslySetInnerHTML={{ __html: message.body }} />
        ) : (
          <pre>{message.body}</pre>
        )}
      </div>
    </div>
  );
}
