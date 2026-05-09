import type {
  CalendarEvent,
  CalendarEventInput,
  CalendarEventListResponse,
} from '../types/google.ts';

const CALENDAR_API = 'https://www.googleapis.com/calendar/v3';

export async function listEvents(
  accessToken: string,
  options: {
    timeMin?: string;
    timeMax?: string;
    maxResults?: number;
    pageToken?: string;
  } = {},
): Promise<{ events: CalendarEvent[]; nextPageToken?: string }> {
  const params = new URLSearchParams({
    orderBy: 'startTime',
    singleEvents: 'true',
    timeMin: options.timeMin ?? new Date().toISOString(),
    maxResults: String(options.maxResults ?? 50),
  });
  if (options.timeMax) params.set('timeMax', options.timeMax);
  if (options.pageToken) params.set('pageToken', options.pageToken);

  const res = await fetch(
    `${CALENDAR_API}/calendars/primary/events?${params}`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );

  if (!res.ok) {
    const body = await res.text();
    console.error('Calendar list error:', res.status, body);
    throw new Error(`Calendar list failed: ${res.status} - ${body}`);
  }

  const data = (await res.json()) as CalendarEventListResponse;
  return {
    events: data.items ?? [],
    nextPageToken: data.nextPageToken,
  };
}

export async function createEvent(
  accessToken: string,
  event: CalendarEventInput,
): Promise<CalendarEvent> {
  const res = await fetch(`${CALENDAR_API}/calendars/primary/events`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(event),
  });

  if (!res.ok) {
    const body = await res.text();
    console.error('Calendar create error:', res.status, body);
    throw new Error(`Calendar create failed: ${res.status} - ${body}`);
  }
  return (await res.json()) as CalendarEvent;
}

export async function updateEvent(
  accessToken: string,
  eventId: string,
  event: CalendarEventInput,
): Promise<CalendarEvent> {
  const res = await fetch(
    `${CALENDAR_API}/calendars/primary/events/${encodeURIComponent(eventId)}`,
    {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(event),
    },
  );

  if (!res.ok) {
    const body = await res.text();
    console.error('Calendar update error:', res.status, body);
    throw new Error(`Calendar update failed: ${res.status} - ${body}`);
  }
  return (await res.json()) as CalendarEvent;
}
