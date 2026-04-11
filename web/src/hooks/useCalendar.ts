import { useState, useCallback } from 'react';
import { getValidAccessToken } from '../services/tokenService.ts';
import {
  listEvents,
  createEvent,
  updateEvent,
} from '../services/calendarService.ts';
import type { CalendarEvent, CalendarEventInput } from '../types/google.ts';

interface UseCalendarReturn {
  events: CalendarEvent[];
  loading: boolean;
  error: string | null;
  fetchEvents: (timeMin?: string, timeMax?: string) => Promise<void>;
  addEvent: (event: CalendarEventInput) => Promise<CalendarEvent>;
  editEvent: (eventId: string, event: CalendarEventInput) => Promise<CalendarEvent>;
}

export function useCalendar(userId: string): UseCalendarReturn {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = useCallback(async (timeMin?: string, timeMax?: string) => {
    setLoading(true);
    setError(null);
    try {
      const token = await getValidAccessToken(userId);
      const result = await listEvents(token, { timeMin, timeMax });
      setEvents(result.events);
    } catch (err) {
      setError(err instanceof Error ? err.message : '캘린더 로드 실패');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const addEvent = useCallback(async (event: CalendarEventInput): Promise<CalendarEvent> => {
    const token = await getValidAccessToken(userId);
    const created = await createEvent(token, event);
    setEvents((prev) => [...prev, created].sort((a, b) => {
      const aTime = a.start.dateTime ?? a.start.date ?? '';
      const bTime = b.start.dateTime ?? b.start.date ?? '';
      return aTime.localeCompare(bTime);
    }));
    return created;
  }, [userId]);

  const editEvent = useCallback(async (eventId: string, event: CalendarEventInput): Promise<CalendarEvent> => {
    const token = await getValidAccessToken(userId);
    const updated = await updateEvent(token, eventId, event);
    setEvents((prev) => prev.map((e) => e.id === eventId ? updated : e));
    return updated;
  }, [userId]);

  return { events, loading, error, fetchEvents, addEvent, editEvent };
}
