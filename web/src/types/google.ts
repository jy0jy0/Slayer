// Google OAuth Token
export interface GoogleTokenRow {
  user_id: string;
  access_token: string;
  refresh_token: string | null;
  token_expires_at: string;
  scopes: string;
  created_at: string;
  updated_at: string;
}

// Gmail Types
export interface GmailMessageHeader {
  name: string;
  value: string;
}

export interface GmailMessagePart {
  mimeType: string;
  body: { data?: string; size: number };
  parts?: GmailMessagePart[];
}

export interface GmailMessage {
  id: string;
  threadId: string;
  snippet: string;
  internalDate: string;
  payload: {
    headers: GmailMessageHeader[];
    mimeType: string;
    body: { data?: string; size: number };
    parts?: GmailMessagePart[];
  };
  labelIds: string[];
}

export interface GmailMessageListItem {
  id: string;
  threadId: string;
}

export interface GmailListResponse {
  messages: GmailMessageListItem[];
  nextPageToken?: string;
  resultSizeEstimate: number;
}

// Parsed Gmail message for display
export interface ParsedGmailMessage {
  id: string;
  threadId: string;
  subject: string;
  from: string;
  to: string;
  date: string;
  snippet: string;
  body: string;
  isUnread: boolean;
}

// Calendar Types
export interface CalendarEventDateTime {
  dateTime?: string;
  date?: string;
  timeZone?: string;
}

export interface CalendarEvent {
  id: string;
  summary: string;
  description?: string;
  location?: string;
  start: CalendarEventDateTime;
  end: CalendarEventDateTime;
  status: string;
  htmlLink: string;
  created: string;
  updated: string;
}

export interface CalendarEventListResponse {
  items: CalendarEvent[];
  nextPageToken?: string;
  summary: string;
  timeZone: string;
}

// For creating/updating events
export interface CalendarEventInput {
  summary: string;
  description?: string;
  location?: string;
  start: CalendarEventDateTime;
  end: CalendarEventDateTime;
}
