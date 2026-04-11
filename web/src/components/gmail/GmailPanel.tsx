import { useEffect } from 'react';
import { Mail, RefreshCw } from 'lucide-react';
import { useGmail } from '../../hooks/useGmail.ts';
import MessageList from './MessageList.tsx';
import MessageDetail from './MessageDetail.tsx';

interface GmailPanelProps {
  userId: string;
}

export default function GmailPanel({ userId }: GmailPanelProps) {
  const {
    messages,
    selectedMessage,
    loading,
    error,
    nextPageToken,
    fetchMessages,
    selectMessage,
    clearSelection,
  } = useGmail(userId);

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  return (
    <div className="panel gmail-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Mail size={18} />
          <h2>Gmail</h2>
        </div>
        <button
          className="icon-btn"
          onClick={() => { clearSelection(); fetchMessages(); }}
          disabled={loading}
          title="새로고침"
        >
          <RefreshCw size={16} className={loading ? 'spinning' : ''} />
        </button>
      </div>

      {error && <div className="panel-error">{error}</div>}

      <div className="panel-content">
        {selectedMessage ? (
          <MessageDetail message={selectedMessage} onBack={clearSelection} />
        ) : (
          <MessageList
            messages={messages}
            onSelect={selectMessage}
            onLoadMore={() => fetchMessages(nextPageToken)}
            hasMore={!!nextPageToken}
            loading={loading}
          />
        )}
      </div>

      {loading && messages.length === 0 && !selectedMessage && (
        <div className="panel-loading">메일을 불러오는 중...</div>
      )}
    </div>
  );
}
