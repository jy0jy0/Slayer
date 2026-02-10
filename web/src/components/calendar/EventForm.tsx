import { useState } from 'react';
import { X } from 'lucide-react';
import type { CalendarEvent, CalendarEventInput } from '../../types/google.ts';

interface EventFormProps {
  editingEvent: CalendarEvent | null;
  onSubmit: (event: CalendarEventInput, eventId?: string) => Promise<void>;
  onCancel: () => void;
}

function toLocalDatetimeStr(isoStr?: string): string {
  if (!isoStr) {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  }
  const d = new Date(isoStr);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export default function EventForm({ editingEvent, onSubmit, onCancel }: EventFormProps) {
  const [summary, setSummary] = useState(editingEvent?.summary ?? '');
  const [description, setDescription] = useState(editingEvent?.description ?? '');
  const [location, setLocation] = useState(editingEvent?.location ?? '');
  const [startStr, setStartStr] = useState(
    toLocalDatetimeStr(editingEvent?.start.dateTime ?? editingEvent?.start.date),
  );
  const [endStr, setEndStr] = useState(
    toLocalDatetimeStr(editingEvent?.end.dateTime ?? editingEvent?.end.date),
  );
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!summary.trim()) return;

    setSubmitting(true);
    try {
      const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const eventInput: CalendarEventInput = {
        summary: summary.trim(),
        description: description.trim() || undefined,
        location: location.trim() || undefined,
        start: { dateTime: new Date(startStr).toISOString(), timeZone },
        end: { dateTime: new Date(endStr).toISOString(), timeZone },
      };
      await onSubmit(eventInput, editingEvent?.id);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="event-form-overlay">
      <form className="event-form" onSubmit={handleSubmit}>
        <div className="event-form-header">
          <h3>{editingEvent ? '일정 수정' : '새 일정'}</h3>
          <button type="button" className="icon-btn" onClick={onCancel}>
            <X size={18} />
          </button>
        </div>

        <div className="form-group">
          <label htmlFor="event-summary">제목</label>
          <input
            id="event-summary"
            type="text"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="일정 제목"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="event-start">시작</label>
          <input
            id="event-start"
            type="datetime-local"
            value={startStr}
            onChange={(e) => setStartStr(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="event-end">종료</label>
          <input
            id="event-end"
            type="datetime-local"
            value={endStr}
            onChange={(e) => setEndStr(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="event-location">장소</label>
          <input
            id="event-location"
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="장소 (선택)"
          />
        </div>

        <div className="form-group">
          <label htmlFor="event-description">설명</label>
          <textarea
            id="event-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="설명 (선택)"
            rows={3}
          />
        </div>

        <div className="form-actions">
          <button type="button" className="btn-secondary" onClick={onCancel}>
            취소
          </button>
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? '저장 중...' : editingEvent ? '수정' : '생성'}
          </button>
        </div>
      </form>
    </div>
  );
}
