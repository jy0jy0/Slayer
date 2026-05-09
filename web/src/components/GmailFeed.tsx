import { Mail, RefreshCw } from 'lucide-react'
import type { GmailEvent } from '../types'

const STATUS_ICON: Record<string, { icon: string; color: string }> = {
  PASS:      { icon: '✅', color: '#10b981' },
  INTERVIEW: { icon: '📅', color: '#3b82f6' },
  FAIL:      { icon: '❌', color: '#ef4444' },
  REJECT:    { icon: '❌', color: '#ef4444' },
}

interface Props {
  events: GmailEvent[]
  onPoll: () => void
  polling: boolean
}

export default function GmailFeed({ events, onPoll, polling }: Props) {
  return (
    <div className="w-72 shrink-0 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Mail size={14} className="text-zinc-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-600">
            채용 메일
          </span>
          <span className="text-xs bg-zinc-100 text-zinc-500 px-1.5 py-0.5 rounded-full border border-zinc-200">
            {events.length}
          </span>
        </div>
        <button
          onClick={onPoll}
          disabled={polling}
          className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-600 transition-colors disabled:opacity-40"
          title="Gmail 폴링"
        >
          <RefreshCw size={13} className={polling ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex-1 flex flex-col gap-2 overflow-y-auto max-h-[calc(100vh-200px)]">
        {events.length === 0 ? (
          <div className="text-xs text-zinc-400 text-center mt-8">
            감지된 채용 메일이 없습니다
          </div>
        ) : (
          events.map(ev => {
            const st = STATUS_ICON[ev.status_type ?? ''] ?? { icon: '📧', color: '#a1a1aa' }
            const date = ev.received_at
              ? new Date(ev.received_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
              : ''
            return (
              <div
                key={ev.id}
                className="bg-white rounded-lg p-3 border border-zinc-200 hover:border-zinc-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm">{st.icon}</span>
                    <span className="text-sm font-semibold text-zinc-900">{ev.company ?? '?'}</span>
                  </div>
                  <span className="text-xs text-zinc-400">{date}</span>
                </div>
                {ev.stage && (
                  <span
                    className="text-xs px-1.5 py-0.5 rounded-full"
                    style={{ backgroundColor: st.color + '15', color: st.color }}
                  >
                    {ev.stage}
                  </span>
                )}
                {ev.summary && (
                  <p className="text-xs text-zinc-500 mt-1.5 leading-relaxed line-clamp-2">
                    {ev.summary}
                  </p>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
