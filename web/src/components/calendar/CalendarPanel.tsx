import { useEffect, useState } from 'react';
import { CalendarDays, Plus, RefreshCw } from 'lucide-react';
import { useCalendar } from '../../hooks/useCalendar.ts';
import type { CalendarEvent, CalendarEventInput } from '../../types/google.ts';
import EventList from './EventList.tsx';
import EventForm from './EventForm.tsx';

interface CalendarPanelProps {
  userId: string;
}

export default function CalendarPanel({ userId }: CalendarPanelProps) {
  const { events, loading, error, fetchEvents, addEvent, editEvent } = useCalendar(userId);
  const [showForm, setShowForm] = useState(false);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handleEdit = (event: CalendarEvent) => {
    setEditingEvent(event);
    setShowForm(true);
  };

  const handleSubmit = async (eventInput: CalendarEventInput, eventId?: string) => {
    if (eventId) {
      await editEvent(eventId, eventInput);
    } else {
      await addEvent(eventInput);
    }
    setShowForm(false);
    setEditingEvent(null);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingEvent(null);
  };

  return (
    <div className="panel calendar-panel">
      <div className="panel-header">
        <div className="panel-title">
          <CalendarDays size={18} />
          <h2>Calendar</h2>
        </div>
        <div className="panel-actions">
          <button
            className="icon-btn"
            onClick={() => { setEditingEvent(null); setShowForm(true); }}
            title="새 일정"
          >
            <Plus size={16} />
          </button>
          <button
            className="icon-btn"
            onClick={() => fetchEvents()}
            disabled={loading}
            title="새로고침"
          >
            <RefreshCw size={16} className={loading ? 'spinning' : ''} />
          </button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      <div className="panel-content">
        <EventList events={events} onEdit={handleEdit} loading={loading} />
      </div>

      {loading && events.length === 0 && (
        <div className="panel-loading">일정을 불러오는 중...</div>
      )}

      {showForm && (
        <EventForm
          editingEvent={editingEvent}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
        />
      )}
    </div>
  );
}
