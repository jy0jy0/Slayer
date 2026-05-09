import { useState } from "react";
import { Mail, RefreshCw } from "lucide-react";
import { fetchGmailEvents, pollGmail } from "../services/api";
import type { GmailEvent } from "../types";

const STATUS_META: Record<
  string,
  { icon: string; label: string; color: string }
> = {
  PASS: { icon: "✅", label: "합격/통과", color: "#10b981" },
  INTERVIEW: { icon: "📅", label: "면접 안내", color: "#3b82f6" },
  FAIL: { icon: "❌", label: "불합격", color: "#ef4444" },
  REJECT: { icon: "🚫", label: "거절", color: "#6b7280" },
};

interface Props {
  userId: string;
}

export default function GmailMonitorPage({ userId }: Props) {
  const [events, setEvents] = useState<GmailEvent[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState("");
  const [pollResult, setPollResult] = useState<{ processed: number } | null>(
    null,
  );

  const handlePoll = async () => {
    setError("");
    setPollResult(null);
    setPolling(true);
    try {
      const result = await pollGmail(userId);
      setPollResult(result);
      const data = await fetchGmailEvents(userId);
      setEvents(data);
      setLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gmail 폴링 실패");
    } finally {
      setPolling(false);
    }
  };

  const handleLoad = async () => {
    setError("");
    setPolling(true);
    try {
      const data = await fetchGmailEvents(userId);
      setEvents(data);
      setLoaded(true);
    } finally {
      setPolling(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <h1 className="page-title">Gmail Monitor</h1>
        <p className="page-subtitle">
          채용 관련 메일을 자동 감지하고 지원 상태를 업데이트합니다.
        </p>
      </div>

      {/* 컨트롤 */}
      <div className="surface-card p-5 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-zinc-900">
              새 채용 메일 확인
            </p>
            <p className="text-xs text-zinc-500 mt-0.5">
              마지막 확인 이후 수신된 채용 메일을 분류합니다.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleLoad}
              disabled={polling}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-zinc-200
                hover:bg-zinc-50 text-sm text-zinc-600 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={polling ? "animate-spin" : ""} />
              기록 보기
            </button>
            <button
              onClick={handlePoll}
              disabled={polling}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-lime-600 hover:bg-lime-700
                text-white text-sm font-semibold transition-colors disabled:opacity-50"
            >
              <Mail size={14} />
              {polling ? "확인 중..." : "메일 확인"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert-danger px-4 py-3 text-sm mb-4">{error}</div>
      )}

      {/* 결과 */}
      {loaded && (
        <div className="flex flex-col gap-3">
          {pollResult !== null && (
            <div
              className={`rounded-xl px-4 py-3 text-sm font-medium border ${
                pollResult.processed > 0
                  ? "alert-success"
                  : "surface-inline text-zinc-600"
              }`}
            >
              {pollResult.processed > 0
                ? `📬 ${pollResult.processed}건의 채용 메일을 새로 처리했습니다.`
                : "새로 처리된 채용 메일이 없습니다."}
            </div>
          )}
          {events.length === 0 ? (
            <div className="surface-card-soft p-8 text-center">
              <p className="text-sm text-zinc-500">
                감지된 채용 관련 메일이 없습니다.
              </p>
            </div>
          ) : (
            <>
              <div className="surface-inline px-4 py-3 text-sm text-zinc-600">
                총 {events.length}건의 채용 메일 기록
              </div>
              {events.map((ev) => {
                const meta = STATUS_META[ev.status_type ?? ""] ?? {
                  icon: "📧",
                  label: ev.status_type ?? "",
                  color: "#a1a1aa",
                };
                return (
                  <div key={ev.id} className="surface-card p-5 ui-hover-lift">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">{meta.icon}</span>
                          <span className="font-semibold text-zinc-900">
                            {ev.company ?? "회사 미상"}
                          </span>
                          {ev.stage && (
                            <span className="text-xs text-zinc-500">
                              — {ev.stage}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mb-2">
                          <span
                            className="text-xs px-2 py-0.5 rounded-full font-medium"
                            style={{
                              backgroundColor: meta.color + "15",
                              color: meta.color,
                            }}
                          >
                            {meta.label}
                          </span>
                          {ev.received_at && (
                            <span className="text-xs text-zinc-400">
                              {new Date(ev.received_at).toLocaleDateString(
                                "ko-KR",
                                {
                                  month: "short",
                                  day: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                },
                              )}
                            </span>
                          )}
                        </div>
                        {ev.subject && (
                          <p className="text-sm text-zinc-700 mb-1">
                            {ev.subject}
                          </p>
                        )}
                        {ev.summary && (
                          <p className="text-xs text-zinc-500 leading-relaxed">
                            {ev.summary}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}

      {!loaded && (
        <div className="text-center py-16 text-zinc-400">
          <Mail size={40} className="mx-auto mb-3 text-zinc-300" />
          <p className="text-sm">버튼을 눌러 Gmail 채용 메일을 확인하세요.</p>
          <p className="text-xs mt-1 text-zinc-400">
            Gmail 연동이 필요합니다 (Google OAuth 로그인)
          </p>
        </div>
      )}
    </div>
  );
}
