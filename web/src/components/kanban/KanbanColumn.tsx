import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import type { Application, AppStatus } from '../../types'
import { STATUS_META } from '../../types'
import ApplicationCard from './ApplicationCard'

interface Props {
  status: AppStatus
  apps: Application[]
}

export default function KanbanColumn({ status, apps }: Props) {
  const meta = STATUS_META[status]
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <div className="flex flex-col w-60 shrink-0">
      {/* 컬럼 헤더 */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: meta.color }} />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            {meta.label}
          </span>
        </div>
        <span
          className="text-xs font-bold px-1.5 py-0.5 rounded-full"
          style={{ backgroundColor: meta.color + '15', color: meta.color }}
        >
          {apps.length}
        </span>
      </div>

      {/* 카드 리스트 */}
      <div
        ref={setNodeRef}
        className={`
          flex-1 min-h-32 rounded-xl p-2 flex flex-col gap-2 transition-colors
          ${isOver ? 'bg-lime-50 ring-1 ring-lime-300' : 'bg-zinc-100/50'}
        `}
      >
        <SortableContext
          items={apps.map(a => a.application_id)}
          strategy={verticalListSortingStrategy}
        >
          {apps.map(app => (
            <ApplicationCard key={app.application_id} app={app} />
          ))}
        </SortableContext>

        {apps.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <span className="text-xs text-zinc-400">비어있음</span>
          </div>
        )}
      </div>
    </div>
  )
}
