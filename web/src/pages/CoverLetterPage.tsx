import { useState } from "react";
import { PenLine, Copy, CheckCheck, AlertCircle } from "lucide-react";
import { generateCoverLetter } from "../services/api";
import { useAppContext } from "../context/AppContext";
import type { CoverLetterOutput } from "../types";
import type { LayoutPageKey } from "../components/Layout";

interface Props {
  onNavigate: (page: LayoutPageKey) => void;
}

export default function CoverLetterPage({ onNavigate }: Props) {
  const { jd, resume, matchResult, companyResearch } = useAppContext();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CoverLetterOutput | null>(null);
  const [copied, setCopied] = useState(false);

  const canRun = !!(jd && resume);

  const handleGenerate = async () => {
    if (!canRun) return;
    setError("");
    setLoading(true);
    try {
      const data = await generateCoverLetter({
        parsed_resume: resume!,
        jd: jd!,
        company_research: companyResearch ?? null,
        match_result: matchResult ?? null,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "자소서 생성 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.cover_letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <h1 className="page-title">Cover Letter Engine</h1>
        <p className="page-subtitle">
          JD, 이력서, 기업 리서치 기반으로 맞춤형 자소서를 생성합니다.
        </p>
      </div>

      {/* 준비 상태 — 4개 배지 */}
      <div className="flex flex-wrap gap-2 mb-5">
        {[
          {
            label: "JD",
            ready: !!jd,
            detail: jd ? jd.company : null,
            page: "jd-match" as LayoutPageKey,
            required: true,
          },
          {
            label: "이력서",
            ready: !!resume,
            detail: resume?.personal_info?.name,
            page: "jd-match" as LayoutPageKey,
            required: true,
          },
          {
            label: "기업 리서치",
            ready: !!companyResearch,
            detail: companyResearch?.company_name,
            page: "company-research" as LayoutPageKey,
            required: false,
          },
          {
            label: "매칭 결과",
            ready: !!matchResult,
            detail: matchResult
              ? `ATS ${matchResult.ats_score.toFixed(0)}`
              : null,
            page: "jd-match" as LayoutPageKey,
            required: false,
          },
        ].map(({ label, ready, detail, page, required }) => (
          <button
            key={label}
            onClick={() => !ready && onNavigate(page)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium transition-all ${
              ready
                ? "bg-lime-50 border-lime-200 text-lime-700 cursor-default"
                : required
                  ? "bg-red-50 border-red-200 text-red-600 hover:bg-red-100"
                  : "bg-zinc-100 border-zinc-200 text-zinc-500 hover:bg-zinc-200"
            }`}
          >
            <span>{ready ? "✓" : required ? "!" : "○"}</span>
            <span>{label}</span>
            {ready && detail && (
              <span className="text-zinc-400 font-normal">— {detail}</span>
            )}
            {!ready && required && <span>필수</span>}
          </button>
        ))}
      </div>

      {!canRun && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-2 mb-5">
          <AlertCircle size={15} className="text-amber-500 mt-0.5 shrink-0" />
          <p className="text-sm text-amber-800">
            JD Match 페이지에서 JD 파싱과 이력서 업로드를 완료해야 자소서를
            생성할 수 있습니다.
          </p>
        </div>
      )}

      {canRun && !result && (
        <div className="bg-white border border-zinc-200 rounded-xl p-5 mb-4">
          <h3 className="text-sm font-semibold text-zinc-800 mb-3">
            생성 정보 확인
          </h3>
          <div className="flex gap-4 text-sm text-zinc-600">
            <div>
              <span className="text-xs text-zinc-400">대상 기업</span>
              <p className="font-medium text-zinc-900 mt-0.5">
                {jd?.company ?? "—"}
              </p>
            </div>
            <div className="w-px bg-zinc-100" />
            <div>
              <span className="text-xs text-zinc-400">포지션</span>
              <p className="font-medium text-zinc-900 mt-0.5">
                {jd?.title ?? "—"}
              </p>
            </div>
            <div className="w-px bg-zinc-100" />
            <div>
              <span className="text-xs text-zinc-400">지원자</span>
              <p className="font-medium text-zinc-900 mt-0.5">
                {resume?.personal_info?.name ?? "—"}
              </p>
            </div>
            {matchResult && (
              <>
                <div className="w-px bg-zinc-100" />
                <div>
                  <span className="text-xs text-zinc-400">ATS 점수</span>
                  <p className="font-medium text-lime-600 mt-0.5">
                    {matchResult.ats_score.toFixed(0)}
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <button
        onClick={handleGenerate}
        disabled={!canRun || loading}
        className={`w-full py-3.5 rounded-xl text-sm font-semibold transition-all flex items-center
          justify-center gap-2 mb-4 ${
            canRun && !loading
              ? "bg-lime-600 hover:bg-lime-700 text-white shadow-sm"
              : "bg-zinc-100 text-zinc-400 cursor-not-allowed"
          }`}
      >
        <PenLine size={15} />
        {loading
          ? "AI 자소서 작성 중..."
          : result
            ? "다시 생성"
            : "자소서 생성"}
      </button>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600 mb-4">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-white border border-zinc-200 rounded-xl p-10 text-center">
          <PenLine
            size={24}
            className="mx-auto text-lime-600 animate-pulse mb-3"
          />
          <p className="text-sm font-medium text-zinc-700">자소서 작성 중...</p>
          <p className="text-xs text-zinc-400 mt-1">
            JD 키워드 · 이력서 · 기업 정보를 분석해 맞춤형 내용을 작성합니다
          </p>
        </div>
      )}

      {result && !loading && (
        <div className="flex flex-col gap-4">
          {/* 메트릭 */}
          <div className="grid grid-cols-3 gap-3">
            {[
              {
                label: "키워드 커버리지",
                value: `${(result.jd_keyword_coverage * 100).toFixed(0)}%`,
                color: "text-lime-600",
              },
              {
                label: "글자 수",
                value: result.word_count.toLocaleString(),
                color: "text-zinc-800",
              },
              {
                label: "핵심 포인트",
                value: result.key_points?.length ?? 0,
                color: "text-zinc-800",
              },
            ].map(({ label, value, color }) => (
              <div
                key={label}
                className="bg-white border border-zinc-200 rounded-xl p-4 text-center"
              >
                <p className="text-xs text-zinc-400 mb-1">{label}</p>
                <p className={`text-xl font-bold ${color}`}>{value}</p>
              </div>
            ))}
          </div>

          {/* 핵심 포인트 */}
          {result.key_points && result.key_points.length > 0 && (
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
                전략적 핵심 포인트
              </h3>
              <div className="flex flex-col gap-2">
                {result.key_points.map((p, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <span className="text-lime-600 shrink-0 mt-0.5">✅</span>
                    <span className="text-zinc-700 leading-relaxed">{p}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 자소서 본문 */}
          <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-zinc-100">
              <h3 className="text-sm font-semibold text-zinc-900">
                자기소개서
              </h3>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-zinc-200
                  hover:bg-zinc-50 text-zinc-600 transition-colors"
              >
                {copied ? (
                  <CheckCheck size={12} className="text-lime-600" />
                ) : (
                  <Copy size={12} />
                )}
                {copied ? "복사됨" : "복사"}
              </button>
            </div>
            <div className="px-5 py-4 text-sm text-zinc-800 leading-relaxed whitespace-pre-wrap bg-zinc-50/50 min-h-48">
              {result.cover_letter}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
