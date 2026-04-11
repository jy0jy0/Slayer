import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Calendar, Star } from 'lucide-react'
import type { Application } from '../../types'
import { STATUS_META } from '../../types'

interface Props {
  app: Application
  isDragging?: boolean
}

export default function ApplicationCard({ app, isDragging }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: app.application_id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const meta = STATUS_META[app.status]
  const date = app.applied_at
    ? new Date(app.applied_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
    : app.deadline
    ? `마감 ${new Date(app.deadline).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}`
    : null

  return (
    <div
      ref={setNodeRef}
      style={{ ...style, borderLeftColor: meta.color }}
      {...attributes}
      {...listeners}
      className="bg-white rounded-lg border border-zinc-200 border-l-4 p-3 cursor-grab active:cursor-grabbing hover:shadow-sm hover:border-zinc-300 transition-all select-none"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center text-xs font-bold shrink-0"
            style={{ backgroundColor: meta.color + '15', color: meta.color }}
          >
            {(app.company ?? '?')[0].toUpperCase()}
          </div>
          <span className="font-semibold text-sm text-zinc-900 truncate">
            {app.company ?? '회사 미상'}
          </span>
        </div>
        {app.ats_score != null && (
          <div className="flex items-center gap-1 shrink-0">
            <Star size={10} className="text-amber-500 fill-amber-500" />
            <span className="text-xs text-amber-600">{app.ats_score.toFixed(0)}</span>
          </div>
        )}
      </div>

      {date && (
        <div className="flex items-center gap-1 mt-2">
          <Calendar size={10} className="text-zinc-400" />
          <span className="text-xs text-zinc-400">{date}</span>
        </div>
      )}
    </div>
  )
}
