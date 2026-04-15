import { useCallback, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { ChevronDown, ChevronRight, Mail, X } from "lucide-react";
import type { Application, AppStatus, GmailEvent } from "../../types";
import { BOARD_COLUMNS, BOARD_GROUPS, STATUS_META } from "../../types";
import { updateStatus } from "../../services/api";
import ApplicationCard from "./ApplicationCard";

const STATUS_ICON: Record<string, string> = {
  PASS: "✅",
  INTERVIEW: "📅",
  FAIL: "❌",
  REJECT: "🚫",
};

function normalizeCompany(value: string | null | undefined) {
  return value?.trim().toLowerCase() ?? "";
}

interface StatusLaneProps {
  status: AppStatus;
  apps: Application[];
  collapsed: boolean;
  onToggle: () => void;
  onCardClick: (app: Application) => void;
}

function StatusLane({
  status,
  apps,
  collapsed,
  onToggle,
  onCardClick,
}: StatusLaneProps) {
  const meta = STATUS_META[status];
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div className="rounded-xl border border-zinc-200 bg-white/85 shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-zinc-50 transition-colors"
      >
        <span className="text-zinc-400 shrink-0">
          {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
        </span>
        <span
          className="w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: meta.color }}
        />
        <span className="text-xs font-semibold text-zinc-700 truncate">
          {meta.label}
        </span>
        <span
          className="ml-auto text-[11px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
          style={{ backgroundColor: `${meta.color}18`, color: meta.color }}
        >
          {apps.length}
        </span>
      </button>

      {!collapsed && (
        <div
          ref={setNodeRef}
          className={`min-h-40 border-t border-zinc-100 p-2.5 transition-colors ${
            isOver
              ? "bg-lime-50 ring-1 ring-inset ring-lime-300"
              : "bg-transparent"
          }`}
        >
          <SortableContext
            items={apps.map((app) => app.application_id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="flex flex-col gap-2">
              {apps.map((app) => (
                <ApplicationCard
                  key={app.application_id}
                  app={app}
                  onClick={() => onCardClick(app)}
                />
              ))}
            </div>
          </SortableContext>
        </div>
      )}
    </div>
  );
}

interface GroupColumnProps {
  groupKey: string;
  children: React.ReactNode;
  isOverActive: boolean;
}

function GroupColumnShell({
  groupKey,
  children,
  isOverActive,
}: GroupColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: groupKey });
  const active = isOver || isOverActive;

  return (
    <div
      ref={setNodeRef}
      className={`rounded-2xl transition-colors ${active ? "bg-lime-50/70 ring-1 ring-inset ring-lime-300" : ""}`}
    >
      {children}
    </div>
  );
}

interface Props {
  apps: Application[];
  userId: string;
  gmailEvents?: GmailEvent[];
  onRefresh: () => void | Promise<void>;
}

export default function KanbanBoard({
  apps,
  userId,
  gmailEvents = [],
  onRefresh,
}: Props) {
  const [draggingApp, setDraggingApp] = useState<Application | null>(null);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<
    Record<string, boolean>
  >({});
  const [collapsedLanes, setCollapsedLanes] = useState<Record<string, boolean>>(
    {},
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

  const grouped = BOARD_COLUMNS.reduce<Record<AppStatus, Application[]>>(
    (acc, status) => {
      acc[status] = apps.filter((app) => app.status === status);
      return acc;
    },
    {} as Record<AppStatus, Application[]>,
  );

  const toggleGroup = useCallback((key: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const toggleLane = useCallback((key: string) => {
    setCollapsedLanes((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      setDraggingApp(
        apps.find((app) => app.application_id === event.active.id) ?? null,
      );
    },
    [apps],
  );

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      setDraggingApp(null);

      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const app = apps.find((item) => item.application_id === active.id);
      if (!app) return;

      let newStatus: AppStatus | undefined;

      const overGroup = BOARD_GROUPS.find((group) => group.key === over.id);
      if (overGroup) {
        const visibleStatuses = overGroup.statuses.filter(
          (status) => (grouped[status]?.length ?? 0) > 0,
        );
        newStatus = visibleStatuses[0] ?? overGroup.statuses[0];
      } else if (BOARD_COLUMNS.includes(over.id as AppStatus)) {
        newStatus = over.id as AppStatus;
      } else {
        newStatus = apps.find(
          (item) => item.application_id === over.id,
        )?.status;
      }

      if (!newStatus || newStatus === app.status) return;

      await updateStatus(app.application_id, userId, newStatus);
      await Promise.resolve(onRefresh());
    },
    [apps, grouped, onRefresh, userId],
  );

  const selectedMeta = selectedApp ? STATUS_META[selectedApp.status] : null;
  const selectedCompanyKey = normalizeCompany(selectedApp?.company);

  const relatedEvents = selectedCompanyKey
    ? [...gmailEvents]
        .filter(
          (event) => normalizeCompany(event.company) === selectedCompanyKey,
        )
        .sort((a, b) => {
          const aTime = a.received_at ? new Date(a.received_at).getTime() : 0;
          const bTime = b.received_at ? new Date(b.received_at).getTime() : 0;
          return bTime - aTime;
        })
    : [];

  return (
    <div className="flex gap-4 h-full min-h-0">
      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div
          className={`min-w-0 min-h-0 grid gap-4 transition-all duration-300 ${selectedApp ? "flex-3" : "flex-1"} grid-cols-1 xl:grid-cols-3`}
        >
          {BOARD_GROUPS.map((group) => {
            const groupApps = group.statuses.flatMap(
              (status) => grouped[status] ?? [],
            );
            const visibleStatuses = group.statuses.filter(
              (status) => (grouped[status]?.length ?? 0) > 0,
            );
            const isGroupCollapsed = !!collapsedGroups[group.key];

            return (
              <section
                key={group.key}
                className={`rounded-2xl border ${group.bgClass} overflow-hidden min-h-0`}
              >
                <button
                  type="button"
                  onClick={() => toggleGroup(group.key)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left"
                  style={{ borderTop: `3px solid ${group.accentColor}` }}
                >
                  <span className="text-zinc-400 shrink-0">
                    {isGroupCollapsed ? (
                      <ChevronRight size={15} />
                    ) : (
                      <ChevronDown size={15} />
                    )}
                  </span>

                  <div className="min-w-0">
                    <div className="text-sm font-bold text-zinc-800">
                      {group.label}
                    </div>
                    <div className="text-[11px] text-zinc-500 mt-0.5">
                      {groupApps.length > 0
                        ? `${groupApps.length}개 지원서`
                        : "현재 항목 없음"}
                    </div>
                  </div>

                  <div className="ml-auto flex items-center gap-1.5 flex-wrap justify-end">
                    {group.statuses.map((status) => {
                      const count = grouped[status]?.length ?? 0;
                      if (count === 0) return null;
                      const meta = STATUS_META[status];

                      return (
                        <span
                          key={status}
                          className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
                          style={{
                            backgroundColor: `${meta.color}18`,
                            color: meta.color,
                          }}
                        >
                          {meta.label} {count}
                        </span>
                      );
                    })}

                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded-full shrink-0"
                      style={{
                        backgroundColor: `${group.accentColor}20`,
                        color: group.accentColor,
                      }}
                    >
                      {groupApps.length}
                    </span>
                  </div>
                </button>

                {!isGroupCollapsed && (
                  <div className="px-4 pb-4 min-h-0">
                    <GroupColumnShell groupKey={group.key} isOverActive={false}>
                      {visibleStatuses.length === 0 ? (
                        <div className="min-h-24 rounded-xl border border-dashed border-zinc-200 bg-white/70 flex items-center justify-center text-xs text-zinc-400">
                          현재 항목 없음
                        </div>
                      ) : (
                        <div className="flex flex-col gap-3 min-h-0">
                          {visibleStatuses.map((status) => (
                            <StatusLane
                              key={status}
                              status={status}
                              apps={grouped[status] ?? []}
                              collapsed={!!collapsedLanes[status]}
                              onToggle={() => toggleLane(status)}
                              onCardClick={setSelectedApp}
                            />
                          ))}
                        </div>
                      )}
                    </GroupColumnShell>
                  </div>
                )}
              </section>
            );
          })}
        </div>

        <DragOverlay>
          {draggingApp ? (
            <ApplicationCard app={draggingApp} isDragging />
          ) : null}
        </DragOverlay>
      </DndContext>

      {selectedApp && selectedMeta && (
        <aside className="flex-[1.2] min-w-70 max-w-90 flex flex-col bg-white rounded-2xl border border-zinc-200 overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-zinc-100 flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div
                className="font-bold text-sm text-zinc-900 truncate"
                style={{
                  borderLeft: `3px solid ${selectedMeta.color}`,
                  paddingLeft: 8,
                }}
              >
                {selectedApp.company ?? "회사 미상"}
              </div>
              <div className="text-[11px] text-zinc-400 mt-0.5 pl-2">
                {selectedMeta.label}
              </div>
            </div>

            <button
              type="button"
              onClick={() => setSelectedApp(null)}
              className="p-1 rounded-lg hover:bg-zinc-100 text-zinc-400 hover:text-zinc-600 transition-colors shrink-0"
            >
              <X size={14} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
            <div className="flex items-center gap-1.5 mb-1">
              <Mail size={12} className="text-zinc-400" />
              <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                채용 메일 {relatedEvents.length}건
              </span>
            </div>

            {relatedEvents.length === 0 ? (
              <div className="flex-1 flex items-center justify-center py-8">
                <span className="text-xs text-zinc-400">관련 메일 없음</span>
              </div>
            ) : (
              relatedEvents.map((event) => {
                const icon = STATUS_ICON[event.status_type ?? ""] ?? "📧";
                const date = event.received_at
                  ? new Date(event.received_at).toLocaleDateString("ko-KR", {
                      month: "short",
                      day: "numeric",
                    })
                  : "";

                return (
                  <div
                    key={event.id}
                    className="rounded-xl border border-zinc-100 bg-zinc-50 p-3"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm">{icon}</span>
                        {event.stage && (
                          <span className="text-[11px] font-semibold text-zinc-700">
                            {event.stage}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-zinc-400">{date}</span>
                    </div>

                    {event.subject && (
                      <p className="text-xs text-zinc-600 font-medium mb-1 line-clamp-1">
                        {event.subject}
                      </p>
                    )}

                    {event.summary && (
                      <p className="text-[11px] text-zinc-500 leading-relaxed line-clamp-3">
                        {event.summary}
                      </p>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </aside>
      )}
    </div>
  );
}
