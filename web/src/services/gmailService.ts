import type {
  GmailListResponse,
  GmailMessage,
  GmailMessagePart,
  ParsedGmailMessage,
} from '../types/google.ts';

const GMAIL_API = 'https://gmail.googleapis.com/gmail/v1/users/me';

function decodeBase64Url(data: string): string {
  const base64 = data.replace(/-/g, '+').replace(/_/g, '/');
  return decodeURIComponent(
    atob(base64)
      .split('')
      .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
      .join(''),
  );
}

function extractBody(payload: GmailMessage['payload']): string {
  // text/plain 우선, 없으면 text/html
  function findPart(parts: GmailMessagePart[] | undefined, mime: string): string | undefined {
    if (!parts) return undefined;
    for (const part of parts) {
      if (part.mimeType === mime && part.body.data) {
        return decodeBase64Url(part.body.data);
      }
      if (part.parts) {
        const found = findPart(part.parts, mime);
        if (found) return found;
      }
    }
    return undefined;
  }

  if (payload.body.data) {
    return decodeBase64Url(payload.body.data);
  }

  return findPart(payload.parts, 'text/plain')
    ?? findPart(payload.parts, 'text/html')
    ?? '';
}

function getHeader(headers: GmailMessage['payload']['headers'], name: string): string {
  return headers.find((h) => h.name.toLowerCase() === name.toLowerCase())?.value ?? '';
}

function parseMessage(msg: GmailMessage): ParsedGmailMessage {
  return {
    id: msg.id,
    threadId: msg.threadId,
    subject: getHeader(msg.payload.headers, 'Subject'),
    from: getHeader(msg.payload.headers, 'From'),
    to: getHeader(msg.payload.headers, 'To'),
    date: getHeader(msg.payload.headers, 'Date'),
    snippet: msg.snippet,
    body: extractBody(msg.payload),
    isUnread: msg.labelIds.includes('UNREAD'),
  };
}

export async function listMessages(
  accessToken: string,
  maxResults = 20,
  pageToken?: string,
): Promise<{ messages: ParsedGmailMessage[]; nextPageToken?: string }> {
  const params = new URLSearchParams({
    maxResults: String(maxResults),
    labelIds: 'INBOX',
  });
  if (pageToken) params.set('pageToken', pageToken);

  const res = await fetch(`${GMAIL_API}/messages?${params}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    const body = await res.text();
    console.error('Gmail list error:', res.status, body);
    throw new Error(`Gmail list failed: ${res.status} - ${body}`);
  }

  const data = (await res.json()) as GmailListResponse;
  if (!data.messages?.length) return { messages: [] };

  // 각 메시지의 상세 정보를 병렬로 가져오기
  const details = await Promise.all(
    data.messages.map((m) => getMessage(accessToken, m.id)),
  );

  return {
    messages: details,
    nextPageToken: data.nextPageToken,
  };
}

export async function getMessage(
  accessToken: string,
  messageId: string,
): Promise<ParsedGmailMessage> {
  const res = await fetch(`${GMAIL_API}/messages/${messageId}?format=full`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    const body = await res.text();
    console.error('Gmail get error:', res.status, body);
    throw new Error(`Gmail get failed: ${res.status} - ${body}`);
  }

  const msg = (await res.json()) as GmailMessage;
  return parseMessage(msg);
}
