import { useState, useEffect, useCallback } from "react";
import { RefreshCw } from "lucide-react";
import type { Session } from "@supabase/supabase-js";
import {
  fetchApplications,
  fetchGmailEvents,
  pollGmail,
} from "../services/api";
import type { Application, GmailEvent } from "../types";
import KanbanBoard from "../components/kanban/KanbanBoard";

interface Props {
  session: Session;
}

export default function DashboardPage({ session }: Props) {
  const userId = session.user.id;

  const [apps, setApps] = useState<Application[]>([]);
  const [gmailEvents, setGmailEvents] = useState<GmailEvent[]>([]);
  const [polling, setPolling] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const loadApps = useCallback(async () => {
    const data = await fetchApplications(userId);
    setApps(data);
  }, [userId]);

  const loadGmailEvents = useCallback(async () => {
    const data = await fetchGmailEvents(userId);
    setGmailEvents(data);
  }, [userId]);

  useEffect(() => {
    const autoSync = async () => {
      await Promise.all([loadApps(), loadGmailEvents()]);
      setPolling(true);
      try {
        const timeout = new Promise<{ processed: number }>((_, reject) =>
          setTimeout(() => reject(new Error("timeout")), 60000),
        );
        const result = await Promise.race([pollGmail(userId), timeout]);
        await Promise.all([loadApps(), loadGmailEvents()]);
        if (result.processed > 0) {
          setSyncMessage(
            `📬 ${result.processed}건의 채용 메일을 처리했습니다.`,
          );
          setTimeout(() => setSyncMessage(null), 4000);
        }
      } catch {
        // keep loaded data
      } finally {
        setPolling(false);
      }
    };

    autoSync();
  }, [userId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePoll = async () => {
    setPolling(true);
    try {
      const result = await pollGmail(userId);
      await Promise.all([loadApps(), loadGmailEvents()]);
      if (result.processed > 0) {
        setSyncMessage(`📬 ${result.processed}건의 채용 메일을 처리했습니다.`);
        setTimeout(() => setSyncMessage(null), 4000);
      }
    } catch {
      // ignore
    } finally {
      setPolling(false);
    }
  };

  const totalApps = apps.length;
  const inProgress = apps.filter((a) => a.status === "in_progress").length;
  const finalPass = apps.filter((a) => a.status === "final_pass").length;

  return (
    <div className="page-shell flex flex-col h-full">
      {syncMessage && !polling && (
        <div className="alert-success px-4 py-2 text-xs font-medium flex items-center gap-2 mb-3">
          {syncMessage}
        </div>
      )}

      <div className="surface-card px-5 py-4 mb-4">
        <div className="flex items-center justify-between gap-4">
          <div className="page-header mb-0">
            <h1 className="page-title">지원 현황</h1>
            <p className="page-subtitle">
              카드를 클릭하면 관련 메일을 확인할 수 있습니다
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="surface-inline px-3 py-1.5 text-xs text-zinc-600 hidden md:flex items-center gap-3">
              <span>
                총 <b className="text-zinc-900">{totalApps}</b>건
              </span>
              <span>
                전형중 <b className="text-amber-700">{inProgress}</b>건
              </span>
              <span>
                최종합격 <b className="text-emerald-700">{finalPass}</b>건
              </span>
            </div>

            <button
              onClick={handlePoll}
              disabled={polling}
              className="ui-focusable ui-hover-lift flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-zinc-200 bg-white/80 text-zinc-600 hover:text-zinc-800 disabled:opacity-40"
              title="Gmail 새로고침"
            >
              <RefreshCw size={12} className={polling ? "animate-spin" : ""} />
              {polling ? "동기화 중..." : "메일 동기화"}
            </button>
          </div>
        </div>
      </div>

      <div className="surface-card-soft flex-1 min-h-0 overflow-auto p-4">
        <KanbanBoard
          apps={apps}
          userId={userId}
          gmailEvents={gmailEvents}
          onRefresh={loadApps}
        />
      </div>
    </div>
  );
}
