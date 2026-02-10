import { useState, useCallback } from 'react';
import { getValidAccessToken } from '../services/tokenService.ts';
import { listMessages, getMessage } from '../services/gmailService.ts';
import type { ParsedGmailMessage } from '../types/google.ts';

interface UseGmailReturn {
  messages: ParsedGmailMessage[];
  selectedMessage: ParsedGmailMessage | null;
  loading: boolean;
  error: string | null;
  nextPageToken: string | undefined;
  fetchMessages: (pageToken?: string) => Promise<void>;
  selectMessage: (messageId: string) => Promise<void>;
  clearSelection: () => void;
}

export function useGmail(userId: string): UseGmailReturn {
  const [messages, setMessages] = useState<ParsedGmailMessage[]>([]);
  const [selectedMessage, setSelectedMessage] = useState<ParsedGmailMessage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextPageToken, setNextPageToken] = useState<string | undefined>();

  const fetchMessages = useCallback(async (pageToken?: string) => {
    setLoading(true);
    setError(null);
    try {
      const token = await getValidAccessToken(userId);
      const result = await listMessages(token, 20, pageToken);
      if (pageToken) {
        setMessages((prev) => [...prev, ...result.messages]);
      } else {
        setMessages(result.messages);
      }
      setNextPageToken(result.nextPageToken);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gmail 로드 실패');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const selectMessage = useCallback(async (messageId: string) => {
    setLoading(true);
    setError(null);
    try {
      const token = await getValidAccessToken(userId);
      const msg = await getMessage(token, messageId);
      setSelectedMessage(msg);
    } catch (err) {
      setError(err instanceof Error ? err.message : '메시지 로드 실패');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const clearSelection = useCallback(() => {
    setSelectedMessage(null);
  }, []);

  return {
    messages,
    selectedMessage,
    loading,
    error,
    nextPageToken,
    fetchMessages,
    selectMessage,
    clearSelection,
  };
}
