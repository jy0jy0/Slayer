import { Calendar } from 'lucide-react';
import type { CalendarEvent } from '../../types/google.ts';

interface EventListProps {
  events: CalendarEvent[];
  onEdit: (event: CalendarEvent) => void;
  loading: boolean;
}

function formatEventTime(event: CalendarEvent): string {
  const start = event.start.dateTime ?? event.start.date ?? '';
  const end = event.end.dateTime ?? event.end.date ?? '';

  if (event.start.date && !event.start.dateTime) {
    // 종일 일정
    return new Date(start).toLocaleDateString('ko-KR', {
      month: 'long',
      day: 'numeric',
    }) + ' (종일)';
  }

  const startDate = new Date(start);
  const endDate = new Date(end);
  const dateStr = startDate.toLocaleDateString('ko-KR', {
    month: 'short',
    day: 'numeric',
  });
  const startTime = startDate.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
  });
  const endTime = endDate.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
  });

  return `${dateStr} ${startTime} - ${endTime}`;
}

export default function EventList({ events, onEdit, loading }: EventListProps) {
  if (!loading && events.length === 0) {
    return <div className="empty-state">예정된 일정이 없습니다.</div>;
  }

  return (
    <div className="event-list">
      {events.map((event) => (
        <div
          key={event.id}
          className="event-item"
          onClick={() => onEdit(event)}
        >
          <div className="event-icon">
            <Calendar size={14} />
          </div>
          <div className="event-info">
            <div className="event-summary">{event.summary}</div>
            <div className="event-time">{formatEventTime(event)}</div>
            {event.location && (
              <div className="event-location">{event.location}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
