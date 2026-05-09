import { useState } from "react";
import { Sparkles, TrendingUp, ArrowRight, AlertCircle } from "lucide-react";
import { runOptimize } from "../services/api";
import { useAppContext } from "../context/AppContext";
import type { LayoutPageKey } from "../components/Layout";

interface Props {
  onNavigate: (page: LayoutPageKey) => void;
}

export default function OptimizePage({ onNavigate }: Props) {
  const { jd, resume, matchResult, setOptimizeResult, optimizeResult, applicationId } =
    useAppContext();

  const [targetScore, setTargetScore] = useState(80);
  const [maxIter, setMaxIter] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canRun = !!(jd && resume && matchResult);

  const handleOptimize = async () => {
    if (!canRun) return;
    setError("");
    setLoading(true);
    try {
      const data = await runOptimize({
        parsed_resume: resume!,
        jd: jd!,
        match_result: matchResult!,
        target_ats_score: targetScore,
        max_iterations: maxIter,
      }, applicationId);
      setOptimizeResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "최적화 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <h1 className="page-title">Resume Optimize</h1>
        <p className="page-subtitle">
          이력서를 반복적으로 개선해 목표 ATS 점수에 도달합니다.
        </p>
      </div>

      {/* 준비 상태 */}
      <div className="grid grid-cols-3 gap-2 mb-5">
        {[
          {
            label: "JD",
            ready: !!jd,
            detail: jd
              ? `${jd.company ?? "—"} · ${jd.title ?? "—"}`
              : undefined,
            page: "jd-match" as LayoutPageKey,
          },
          {
            label: "이력서",
            ready: !!resume,
            detail: resume?.personal_info?.name ?? undefined,
            page: "jd-match" as LayoutPageKey,
          },
          {
            label: "매칭 결과",
            ready: !!matchResult,
            detail: matchResult
              ? `ATS ${matchResult.ats_score.toFixed(0)}점`
              : undefined,
            page: "jd-match" as LayoutPageKey,
          },
        ].map(({ label, ready, detail, page }) => (
          <button
            key={label}
            onClick={() => !ready && onNavigate(page)}
            className={`p-3 rounded-xl border text-left transition-all ${
              ready
                ? "bg-lime-50 border-lime-200 cursor-default"
                : "bg-white border-dashed border-zinc-300 hover:border-lime-300 cursor-pointer"
            }`}
          >
            <div className="flex items-center gap-1.5 mb-0.5">
              <span
                className={`text-xs ${ready ? "text-lime-600" : "text-zinc-400"}`}
              >
                {ready ? "✓" : "○"}
              </span>
              <span
                className={`text-xs font-semibold ${ready ? "text-lime-800" : "text-zinc-500"}`}
              >
                {label}
              </span>
            </div>
            {ready && detail ? (
              <p className="text-xs text-zinc-500 truncate">{detail}</p>
            ) : (
              <p className="text-xs text-zinc-400">→ 클릭해서 준비</p>
            )}
          </button>
        ))}
      </div>

      {!canRun && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-2 mb-5">
          <AlertCircle size={15} className="text-amber-500 mt-0.5 shrink-0" />
          <p className="text-sm text-amber-800">
            JD Match 페이지에서 JD 파싱 + 이력서 업로드 + 매칭 분석을 먼저
            완료하세요.
          </p>
        </div>
      )}

      {/* 설정 */}
      <div className="bg-white border border-zinc-200 rounded-xl p-5 mb-4">
        <h3 className="text-sm font-semibold text-zinc-800 mb-4">
          최적화 설정
        </h3>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="text-xs text-zinc-500 block mb-2">
              목표 점수{" "}
              <b className="text-zinc-900 text-sm ml-1">{targetScore}</b>
            </label>
            <input
              type="range"
              min={50}
              max={100}
              step={5}
              value={targetScore}
              onChange={(e) => setTargetScore(Number(e.target.value))}
              className="w-full accent-lime-600"
            />
            <div className="flex justify-between text-xs text-zinc-300 mt-1">
              <span>50</span>
              <span>75</span>
              <span>100</span>
            </div>
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-2">
              최대 반복{" "}
              <b className="text-zinc-900 text-sm ml-1">{maxIter}회</b>
            </label>
            <div className="flex gap-1.5 mt-1">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  onClick={() => setMaxIter(n)}
                  className={`flex-1 h-8 rounded-lg text-xs font-medium transition-colors ${
                    maxIter === n
                      ? "bg-lime-600 text-white"
                      : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <button
        onClick={handleOptimize}
        disabled={!canRun || loading}
        className={`w-full py-3.5 rounded-xl text-sm font-semibold transition-all flex items-center
          justify-center gap-2 mb-4 ${
            canRun && !loading
              ? "bg-lime-600 hover:bg-lime-700 text-white shadow-sm"
              : "bg-zinc-100 text-zinc-400 cursor-not-allowed"
          }`}
      >
        <Sparkles size={15} />
        {loading ? "AI 최적화 중..." : "최적화 시작"}
      </button>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600 mb-4">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-white border border-zinc-200 rounded-xl p-10 text-center">
          <Sparkles
            size={24}
            className="mx-auto text-lime-600 animate-pulse mb-3"
          />
          <p className="text-sm font-medium text-zinc-700">
            이력서 최적화 중...
          </p>
          <p className="text-xs text-zinc-400 mt-1">
            최대 {maxIter}회 반복합니다
          </p>
        </div>
      )}

      {optimizeResult && !loading && (
        <div className="flex flex-col gap-4">
          {/* 점수 요약 */}
          <div className="bg-white border border-zinc-200 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={14} className="text-lime-600" />
              <h3 className="text-sm font-semibold text-zinc-800">
                최적화 결과
              </h3>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center mb-4">
              <div className="p-3 bg-zinc-50 rounded-lg">
                <p className="text-xs text-zinc-400 mb-1">반복 횟수</p>
                <p className="text-2xl font-bold text-zinc-800">
                  {optimizeResult.iterations_used}
                </p>
              </div>
              <div className="p-3 bg-lime-50 rounded-lg">
                <p className="text-xs text-zinc-400 mb-1">최종 점수</p>
                <p className="text-2xl font-bold text-lime-600">
                  {optimizeResult.final_ats_score.toFixed(0)}
                </p>
              </div>
              <div className="p-3 bg-emerald-50 rounded-lg">
                <p className="text-xs text-zinc-400 mb-1">향상</p>
                <p className="text-2xl font-bold text-emerald-600">
                  +{optimizeResult.score_improvement.toFixed(0)}
                </p>
              </div>
            </div>
            {optimizeResult.optimization_summary && (
              <p className="text-sm text-zinc-600 p-3 bg-zinc-50 rounded-lg leading-relaxed">
                {optimizeResult.optimization_summary}
              </p>
            )}
          </div>

          {/* 변경사항 */}
          {optimizeResult.changes && optimizeResult.changes.length > 0 && (
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-zinc-800 mb-3">
                변경사항 ({optimizeResult.changes.length}건)
              </h3>
              <div className="flex flex-col gap-3">
                {optimizeResult.changes.map((change, i) => (
                  <div
                    key={i}
                    className="border border-zinc-100 rounded-lg p-3"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      {change.block_type && (
                        <span className="text-xs px-2 py-0.5 bg-zinc-100 text-zinc-600 rounded font-medium">
                          {change.block_type}
                        </span>
                      )}
                      {change.field && (
                        <span className="text-xs text-zinc-400">
                          {change.field}
                        </span>
                      )}
                    </div>
                    {change.before && change.after && (
                      <div className="flex gap-2 items-start text-xs">
                        <div className="flex-1 p-2 bg-red-50 rounded text-red-700 opacity-75 line-through leading-relaxed">
                          {change.before}
                        </div>
                        <ArrowRight
                          size={11}
                          className="text-zinc-300 mt-2 shrink-0"
                        />
                        <div className="flex-1 p-2 bg-emerald-50 rounded text-emerald-700 leading-relaxed">
                          {change.after}
                        </div>
                      </div>
                    )}
                    {change.reason && (
                      <p className="text-xs text-zinc-400 mt-2">
                        💡 {change.reason}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 다음 단계 */}
          <div className="bg-zinc-50 border border-zinc-200 rounded-xl p-4">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
              다음 단계
            </p>
            <div className="flex gap-2">
              {[
                {
                  page: "cover-letter" as LayoutPageKey,
                  label: "자소서 생성",
                  desc: "최적화된 이력서 반영",
                },
                {
                  page: "interview-prep" as LayoutPageKey,
                  label: "면접 준비",
                  desc: "개선된 프로필 기반",
                },
              ].map(({ page, label, desc }) => (
                <button
                  key={page}
                  onClick={() => onNavigate(page)}
                  className="flex-1 p-3 bg-white border border-zinc-200 rounded-lg hover:border-lime-300
                    hover:bg-lime-50 transition-colors text-left group"
                >
                  <p className="text-xs font-semibold text-zinc-900 group-hover:text-lime-700">
                    {label}
                  </p>
                  <p className="text-xs text-zinc-400 mt-0.5">{desc}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
