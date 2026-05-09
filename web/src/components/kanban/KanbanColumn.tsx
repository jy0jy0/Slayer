import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import type { Application, AppStatus, GmailEvent } from '../../types'
import { STATUS_META } from '../../types'
import ApplicationCard from './ApplicationCard'

interface Props {
  status: AppStatus
  apps: Application[]
  gmailEvents: GmailEvent[]
  onCardClick: (app: Application) => void
}

export default function KanbanColumn({ status, apps, gmailEvents: _, onCardClick }: Props) {
  const meta = STATUS_META[status]
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <div className="flex flex-col flex-1 min-w-0">
      {/* 컬럼 헤더 */}
      <div className="flex items-center justify-between mb-2 px-0.5">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: meta.color }} />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 truncate">
            {meta.label}
          </span>
        </div>
        <span
          className="text-[11px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
          style={{ backgroundColor: meta.color + '20', color: meta.color }}
        >
          {apps.length}
        </span>
      </div>

      {/* 카드 리스트 */}
      <div
        ref={setNodeRef}
        className={`
          flex-1 min-h-20 rounded-xl p-1.5 flex flex-col gap-2 transition-colors
          ${isOver ? 'bg-lime-50 ring-1 ring-lime-300' : 'bg-white/60'}
        `}
      >
        <SortableContext
          items={apps.map(a => a.application_id)}
          strategy={verticalListSortingStrategy}
        >
          {apps.map(app => (
            <ApplicationCard
              key={app.application_id}
              app={app}
              onClick={() => onCardClick(app)}
            />
          ))}
        </SortableContext>

        {apps.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <span className="text-[11px] text-zinc-300">없음</span>
          </div>
        )}
      </div>
    </div>
  )
}
