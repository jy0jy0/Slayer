import { useState } from "react";
import {
  Upload,
  BarChart2,
  CheckCircle2,
  XCircle,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { parseJD, uploadResume, runMatch } from "../services/api";
import { useAppContext } from "../context/AppContext";
import type { LayoutPageKey } from "../components/Layout";

interface Props {
  userId: string;
  onNavigate: (page: LayoutPageKey) => void;
}

export default function JDMatchPage({ userId, onNavigate }: Props) {
  const { jd, setJd, resume, setResume, matchResult, setMatchResult } =
    useAppContext();

  const [jdUrl, setJdUrl] = useState("");
  const [jdLoading, setJdLoading] = useState(false);
  const [jdError, setJdError] = useState("");

  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [resumeError, setResumeError] = useState("");

  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState("");

  const handleParseJD = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jdUrl.trim()) return;
    setJdError("");
    setJdLoading(true);
    try {
      const data = await parseJD(jdUrl.trim());
      setJd(data);
    } catch (err) {
      setJdError(err instanceof Error ? err.message : "JD 파싱 실패");
    } finally {
      setJdLoading(false);
    }
  };

  const handleParseResume = async () => {
    if (!resumeFile) return;
    setResumeError("");
    setResumeLoading(true);
    try {
      const { parsed } = await uploadResume(resumeFile, userId);
      setResume(parsed);
    } catch (err) {
      setResumeError(err instanceof Error ? err.message : "이력서 파싱 실패");
    } finally {
      setResumeLoading(false);
    }
  };

  const handleMatch = async () => {
    if (!jd || !resume) return;
    setMatchError("");
    setMatchLoading(true);
    try {
      const result = await runMatch(jd, resume);
      setMatchResult(result);
    } catch (err) {
      setMatchError(err instanceof Error ? err.message : "매칭 실패");
    } finally {
      setMatchLoading(false);
    }
  };

  const scoreColor = matchResult
    ? matchResult.ats_score >= 70
      ? "#10b981"
      : matchResult.ats_score >= 50
        ? "#f59e0b"
        : "#ef4444"
    : "#6b7280";

  const scoreLabel = matchResult
    ? matchResult.ats_score >= 70
      ? "높음"
      : matchResult.ats_score >= 50
        ? "보통"
        : "낮음"
    : "";

  return (
    <div className="page-shell">
      <div className="page-header">
        <h1 className="page-title">JD-Resume Match</h1>
        <p className="page-subtitle">
          채용공고와 이력서를 분석해 ATS 매칭 점수를 계산합니다.
        </p>
      </div>

      {/* Step 1 & 2 — 나란히 */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* JD */}
        <div className="bg-white border border-zinc-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <div
              className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                jd ? "bg-lime-600 text-white" : "bg-zinc-200 text-zinc-500"
              }`}
            >
              1
            </div>
            <h3 className="text-sm font-semibold text-zinc-900">
              채용공고 URL
            </h3>
            {jd && (
              <button
                onClick={() => setJd(null)}
                className="ml-auto text-xs text-zinc-400 hover:text-zinc-600"
              >
                <RefreshCw size={12} />
              </button>
            )}
          </div>

          {jd ? (
            <div className="p-3 bg-lime-50 border border-lime-200 rounded-lg">
              <p className="text-sm font-semibold text-zinc-900">
                {jd.company ?? "—"}
              </p>
              <p className="text-xs text-zinc-600 mt-0.5">{jd.title ?? "—"}</p>
              {Array.isArray(jd.skills) && jd.skills.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {(jd.skills as string[]).slice(0, 5).map((s) => (
                    <span
                      key={s}
                      className="text-xs px-1.5 py-0.5 bg-white border border-lime-200 text-zinc-600 rounded"
                    >
                      {s}
                    </span>
                  ))}
                  {jd.skills.length > 5 && (
                    <span className="text-xs text-zinc-400">
                      +{jd.skills.length - 5}
                    </span>
                  )}
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={handleParseJD} className="flex flex-col gap-2">
              <input
                type="url"
                value={jdUrl}
                onChange={(e) => setJdUrl(e.target.value)}
                placeholder="https://..."
                className="px-3 py-2.5 rounded-lg border border-zinc-200 text-sm text-zinc-900
                  placeholder-zinc-400 focus:outline-none focus:border-lime-500 focus:ring-2
                  focus:ring-lime-100 transition-colors"
              />
              <button
                type="submit"
                disabled={jdLoading || !jdUrl.trim()}
                className="py-2.5 rounded-lg bg-zinc-900 hover:bg-zinc-700 text-white text-sm font-medium
                  transition-colors disabled:opacity-40"
              >
                {jdLoading ? "파싱 중..." : "JD 파싱"}
              </button>
              {jdError && <p className="text-xs text-red-500">{jdError}</p>}
            </form>
          )}
        </div>

        {/* 이력서 */}
        <div className="bg-white border border-zinc-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <div
              className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                resume ? "bg-lime-600 text-white" : "bg-zinc-200 text-zinc-500"
              }`}
            >
              2
            </div>
            <h3 className="text-sm font-semibold text-zinc-900">
              이력서 업로드
            </h3>
            {resume && (
              <button
                onClick={() => setResume(null)}
                className="ml-auto text-xs text-zinc-400 hover:text-zinc-600"
              >
                <RefreshCw size={12} />
              </button>
            )}
          </div>

          {resume ? (
            <div className="p-3 bg-lime-50 border border-lime-200 rounded-lg">
              <p className="text-sm font-semibold text-zinc-900">
                {resume.personal_info?.name ?? "이름 미상"}
              </p>
              <p className="text-xs text-zinc-600 mt-0.5">
                {resume.personal_info?.email ?? ""}
              </p>
              <div className="flex gap-3 mt-2 text-xs text-zinc-500">
                {Array.isArray(resume.skills) && (
                  <span>스킬 {(resume.skills as string[]).length}개</span>
                )}
                {Array.isArray(resume.experiences) && (
                  <span>경력 {(resume.experiences as unknown[]).length}건</span>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <label
                className="flex flex-col items-center justify-center gap-2 p-5 border-2 border-dashed
                border-zinc-200 rounded-lg cursor-pointer hover:border-lime-300 hover:bg-lime-50 transition-colors"
              >
                <Upload size={18} className="text-zinc-400" />
                <span className="text-xs text-zinc-500 text-center">
                  {resumeFile ? resumeFile.name : "PDF, DOCX 파일 선택"}
                </span>
                <input
                  type="file"
                  accept=".pdf,.docx,.md,.txt,.json"
                  className="hidden"
                  onChange={(e) => {
                    setResume(null);
                    setResumeError("");
                    setResumeFile(e.target.files?.[0] ?? null);
                  }}
                />
              </label>

              <p className="text-[11px] text-zinc-500 leading-relaxed">
                지원 형식:{" "}
                <b className="text-zinc-700">PDF, DOCX, MD, TXT, JSON</b>
                <br />
                스캔본 PDF(이미지 위주)는 텍스트 추출이 어려워 실패할 수
                있습니다.
              </p>

              <button
                onClick={handleParseResume}
                disabled={!resumeFile || resumeLoading}
                className="py-2.5 rounded-lg bg-zinc-900 hover:bg-zinc-700 text-white text-sm font-medium
                  transition-colors disabled:opacity-40"
              >
                {resumeLoading ? "파싱 중..." : "이력서 파싱"}
              </button>

              {resumeError && (
                <div className="alert-danger px-3 py-2 text-xs leading-relaxed">
                  <p className="font-semibold mb-1">이력서 파싱 실패</p>
                  <p>{resumeError}</p>
                  <p className="mt-1">
                    • 스캔본 PDF라면 텍스트 선택 가능한 PDF/DOCX로 다시 업로드해
                    주세요.
                  </p>
                  <p>• 파일 형식/손상 여부와 용량을 확인해 주세요.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 매칭 버튼 */}
      <button
        onClick={handleMatch}
        disabled={!jd || !resume || matchLoading}
        className={`w-full py-3.5 rounded-xl text-sm font-semibold transition-all flex items-center
          justify-center gap-2 mb-4 ${
            jd && resume && !matchLoading
              ? "bg-lime-600 hover:bg-lime-700 text-white shadow-sm"
              : "bg-zinc-100 text-zinc-400 cursor-not-allowed"
          }`}
      >
        <BarChart2 size={15} />
        {matchLoading
          ? "AI 분석 중..."
          : !jd || !resume
            ? "JD와 이력서를 먼저 준비하세요"
            : "매칭 분석 시작"}
      </button>

      {matchError && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600 mb-4">
          {matchError}
        </div>
      )}

      {matchLoading && (
        <div className="bg-white border border-zinc-200 rounded-xl p-10 text-center">
          <BarChart2
            size={24}
            className="mx-auto text-lime-600 animate-pulse mb-3"
          />
          <p className="text-sm font-medium text-zinc-700">
            ATS 키워드 분석 중...
          </p>
        </div>
      )}

      {/* 결과 */}
      {matchResult && !matchLoading && (
        <div className="flex flex-col gap-4">
          {/* 점수 카드 */}
          <div className="bg-white border border-zinc-200 rounded-xl p-5">
            <div className="flex items-center gap-6">
              {/* 점수 */}
              <div className="text-center shrink-0">
                <div
                  className="w-20 h-20 rounded-full flex items-center justify-center border-[3px] text-2xl font-bold"
                  style={{ borderColor: scoreColor, color: scoreColor }}
                >
                  {matchResult.ats_score.toFixed(0)}
                </div>
                <p
                  className="text-xs mt-1.5 font-medium"
                  style={{ color: scoreColor }}
                >
                  {scoreLabel}
                </p>
                <p className="text-xs text-zinc-400">ATS 점수</p>
              </div>

              {/* 강점/약점 */}
              <div className="flex-1 grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-xs font-semibold text-zinc-700 mb-2 flex items-center gap-1">
                    <CheckCircle2 size={11} className="text-emerald-500" /> 강점
                  </h4>
                  {matchResult.strengths.slice(0, 3).map((s, i) => (
                    <p
                      key={i}
                      className="text-xs text-zinc-600 mb-1 leading-relaxed"
                    >
                      · {s}
                    </p>
                  ))}
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-zinc-700 mb-2 flex items-center gap-1">
                    <XCircle size={11} className="text-red-400" /> 개선 필요
                  </h4>
                  {matchResult.weaknesses.slice(0, 3).map((w, i) => (
                    <p
                      key={i}
                      className="text-xs text-zinc-600 mb-1 leading-relaxed"
                    >
                      · {w}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 키워드 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white border border-zinc-200 rounded-xl p-4">
              <h4 className="text-xs font-semibold text-emerald-700 mb-3">
                ✅ 매칭 키워드{" "}
                <span className="text-zinc-400 font-normal">
                  ({matchResult.matched_keywords.length})
                </span>
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {matchResult.matched_keywords.map((k) => (
                  <span
                    key={k}
                    className="text-xs px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full"
                  >
                    {k}
                  </span>
                ))}
              </div>
            </div>
            <div className="bg-white border border-zinc-200 rounded-xl p-4">
              <h4 className="text-xs font-semibold text-red-600 mb-3">
                ⚠️ 누락 키워드{" "}
                <span className="text-zinc-400 font-normal">
                  ({matchResult.missing_keywords.length})
                </span>
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {matchResult.missing_keywords.map((k) => (
                  <span
                    key={k}
                    className="text-xs px-2 py-0.5 bg-red-50 text-red-600 border border-red-200 rounded-full"
                  >
                    {k}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {matchResult.gap_summary && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
              {matchResult.gap_summary}
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
                  page: "optimize" as LayoutPageKey,
                  label: "이력서 최적화",
                  desc: "누락 키워드 보완",
                },
                {
                  page: "cover-letter" as LayoutPageKey,
                  label: "자소서 생성",
                  desc: "맞춤형 자소서",
                },
                {
                  page: "interview-prep" as LayoutPageKey,
                  label: "면접 준비",
                  desc: "예상 질문 생성",
                },
              ].map(({ page, label, desc }) => (
                <button
                  key={page}
                  onClick={() => onNavigate(page)}
                  className="flex-1 p-3 bg-white border border-zinc-200 rounded-lg hover:border-lime-300
                    hover:bg-lime-50 transition-colors text-left group"
                >
                  <p className="text-xs font-semibold text-zinc-900 group-hover:text-lime-700 transition-colors">
                    {label}
                  </p>
                  <p className="text-xs text-zinc-400 mt-0.5">{desc}</p>
                  <ArrowRight
                    size={11}
                    className="text-zinc-300 group-hover:text-lime-600 mt-1.5 transition-colors"
                  />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
