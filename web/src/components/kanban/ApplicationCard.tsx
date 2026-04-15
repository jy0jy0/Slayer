import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Star } from "lucide-react";
import type { Application, AppStatus } from "../../types";

interface Props {
  app: Application;
  isDragging?: boolean;
  onClick?: () => void;
}

const CARD_STYLE_BY_STATUS: Record<
  AppStatus,
  { bg: string; border: string; hover: string }
> = {
  scrapped: {
    bg: "bg-slate-100/70",
    border: "border-slate-200/80",
    hover: "hover:bg-slate-100/90",
  },
  reviewing: {
    bg: "bg-blue-100/60",
    border: "border-blue-200/80",
    hover: "hover:bg-blue-100/80",
  },
  applied: {
    bg: "bg-violet-100/60",
    border: "border-violet-200/80",
    hover: "hover:bg-violet-100/80",
  },
  in_progress: {
    bg: "bg-amber-100/60",
    border: "border-amber-200/80",
    hover: "hover:bg-amber-100/80",
  },
  final_pass: {
    bg: "bg-emerald-100/60",
    border: "border-emerald-200/80",
    hover: "hover:bg-emerald-100/80",
  },
  rejected: {
    bg: "bg-rose-100/60",
    border: "border-rose-200/80",
    hover: "hover:bg-rose-100/80",
  },
  withdrawn: {
    bg: "bg-zinc-100/75",
    border: "border-zinc-200/80",
    hover: "hover:bg-zinc-100/90",
  },
};

export default function ApplicationCard({ app, isDragging, onClick }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({
      id: app.application_id,
    });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const tone = CARD_STYLE_BY_STATUS[app.status];

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className={[
        "rounded-lg border px-3 py-2.5 cursor-pointer transition-all select-none backdrop-blur-[1px]",
        tone.bg,
        tone.border,
        tone.hover,
        "hover:shadow-sm",
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-sm text-zinc-900 truncate">
          {app.company ?? "회사 미상"}
        </span>

        {app.ats_score != null && (
          <div className="flex items-center gap-0.5 shrink-0">
            <Star size={9} className="text-amber-400 fill-amber-400" />
            <span className="text-xs text-amber-600 font-medium">
              {app.ats_score.toFixed(0)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
