import { useState, useCallback } from 'react'
import {
  DndContext,
  type DragEndEvent,
  DragOverlay,
  type DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import type { Application, AppStatus } from '../../types'
import { BOARD_COLUMNS } from '../../types'
import KanbanColumn from './KanbanColumn'
import ApplicationCard from './ApplicationCard'
import { updateStatus } from '../../services/api'

interface Props {
  apps: Application[]
  userId: string
  onRefresh: () => void
}

export default function KanbanBoard({ apps, userId, onRefresh }: Props) {
  const [draggingApp, setDraggingApp] = useState<Application | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  )

  const grouped = BOARD_COLUMNS.reduce<Record<AppStatus, Application[]>>((acc, col) => {
    acc[col] = apps.filter(a => a.status === col)
    return acc
  }, {} as Record<AppStatus, Application[]>)

  const handleDragStart = useCallback((e: DragStartEvent) => {
    const app = apps.find(a => a.application_id === e.active.id)
    setDraggingApp(app ?? null)
  }, [apps])

  const handleDragEnd = useCallback(async (e: DragEndEvent) => {
    setDraggingApp(null)
    const { active, over } = e
    if (!over || active.id === over.id) return

    const app = apps.find(a => a.application_id === active.id)
    if (!app) return

    // over가 컬럼 ID인지 카드 ID인지 확인
    const newStatus = BOARD_COLUMNS.includes(over.id as AppStatus)
      ? (over.id as AppStatus)
      : apps.find(a => a.application_id === over.id)?.status

    if (!newStatus || newStatus === app.status) return

    await updateStatus(app.application_id, userId, newStatus)
    onRefresh()
  }, [apps, userId, onRefresh])

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {BOARD_COLUMNS.map(col => (
          <KanbanColumn key={col} status={col} apps={grouped[col]} />
        ))}
      </div>

      <DragOverlay>
        {draggingApp && <ApplicationCard app={draggingApp} isDragging />}
      </DragOverlay>
    </DndContext>
  )
}
