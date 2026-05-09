import { useState } from "react";
import {
  MessageCircleQuestion,
  ChevronDown,
  ChevronUp,
  AlertCircle,
} from "lucide-react";
import { generateInterviewQuestions } from "../services/api";
import { useAppContext } from "../context/AppContext";
import type { InterviewQuestionsOutput } from "../types";
import type { LayoutPageKey } from "../components/Layout";

const CATEGORY_LABELS: Record<string, [string, string]> = {
  기술: ["💻", "Technical"],
  경험: ["📋", "Experience"],
  "상황/행동": ["🎭", "Situational"],
  인성: ["🧠", "Personality"],
  컬처핏: ["🤝", "Culture Fit"],
  "기업 이해도": ["🏢", "Company Knowledge"],
};

function CategoryAccordion({
  category,
  questions,
}: {
  category: string;
  questions: InterviewQuestionsOutput["questions"];
}) {
  const [open, setOpen] = useState(true);
  const [emoji, label] = CATEGORY_LABELS[category] ?? ["❓", category];

  return (
    <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-zinc-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-base">{emoji}</span>
          <span className="text-sm font-semibold text-zinc-800">{label}</span>
          <span className="text-xs text-zinc-400 font-normal">
            ({category})
          </span>
          <span className="text-xs px-1.5 py-0.5 bg-zinc-100 text-zinc-500 rounded-full ml-1">
            {questions.length}
          </span>
        </div>
        {open ? (
          <ChevronUp size={14} className="text-zinc-400" />
        ) : (
          <ChevronDown size={14} className="text-zinc-400" />
        )}
      </button>
      {open && (
        <div className="border-t border-zinc-100 divide-y divide-zinc-100">
          {questions.map((q, i) => (
            <div key={i} className="px-5 py-4">
              <p className="text-sm font-medium text-zinc-900 mb-2 leading-relaxed">
                Q{i + 1}. {q.question}
              </p>
              {q.intent && (
                <p className="text-xs text-zinc-500 mb-2">의도: {q.intent}</p>
              )}
              {q.tip && (
                <div className="bg-blue-50 border-l-2 border-blue-400 px-3 py-2 rounded-r-lg text-xs text-blue-700 mb-2">
                  💡 {q.tip}
                </div>
              )}
              {q.source && (
                <span className="inline-block text-xs px-2 py-0.5 bg-zinc-100 text-zinc-500 rounded">
                  출처: {q.source}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface Props {
  onNavigate: (page: LayoutPageKey) => void;
}

export default function InterviewPrepPage({ onNavigate }: Props) {
  const { jd, resume, matchResult, companyResearch, applicationId } = useAppContext();
  const [qPerCategory, setQPerCategory] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<InterviewQuestionsOutput | null>(null);

  const canRun = !!(jd && resume);

  const handleGenerate = async () => {
    if (!canRun) return;
    setError("");
    setLoading(true);
    try {
      const data = await generateInterviewQuestions({
        jd: jd!,
        resume: resume!,
        company_research: companyResearch ?? null,
        match_result: matchResult ?? null,
        questions_per_category: qPerCategory,
      }, applicationId);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "면접 질문 생성 실패");
    } finally {
      setLoading(false);
    }
  };

  // 카테고리별 그룹화
  const byCategory: Record<string, InterviewQuestionsOutput["questions"]> = {};
  if (result) {
    for (const q of result.questions) {
      const cat =
        typeof q.category === "object" && q.category !== null
          ? ((q.category as { value?: string }).value ?? String(q.category))
          : String(q.category);
      if (!byCategory[cat]) byCategory[cat] = [];
      byCategory[cat].push(q);
    }
  }

  return (
    <div className="page-shell">
      <div className="surface-card px-5 py-4 mb-4">
        <div className="page-header mb-0">
          <h1 className="page-title">Interview Prep</h1>
          <p className="page-subtitle">
            JD와 이력서 기반으로 카테고리별 면접 예상 질문을 생성합니다.
          </p>
        </div>
      </div>

      {/* 준비 상태 */}
      <div className="flex flex-wrap gap-2 mb-5">
        {[
          {
            label: "JD",
            ready: !!jd,
            detail: jd?.company,
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
          </button>
        ))}
      </div>

      {!canRun && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-2 mb-5">
          <AlertCircle size={15} className="text-amber-500 mt-0.5 shrink-0" />
          <p className="text-sm text-amber-800">
            JD Match 페이지에서 JD 파싱과 이력서 업로드를 완료해야 면접 질문을
            생성할 수 있습니다.
          </p>
        </div>
      )}

      {/* 설정 */}
      <div className="bg-white border border-zinc-200 rounded-xl p-5 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-zinc-800">
              카테고리당 질문 수
            </p>
            <p className="text-xs text-zinc-400 mt-0.5">
              기술 · 경험 · 상황/행동 · 인성 · 컬처핏 · 기업 이해도
            </p>
          </div>
          <div className="flex gap-1.5">
            {[1, 2, 3, 5, 7].map((n) => (
              <button
                key={n}
                onClick={() => setQPerCategory(n)}
                className={`w-9 h-9 rounded-lg text-sm font-semibold transition-colors ${
                  qPerCategory === n
                    ? "bg-lime-600 text-white shadow-sm"
                    : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
      </div>

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
        <MessageCircleQuestion size={15} />
        {loading ? "질문 생성 중..." : result ? "다시 생성" : "면접 질문 생성"}
      </button>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600 mb-4">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-white border border-zinc-200 rounded-xl p-10 text-center">
          <MessageCircleQuestion
            size={24}
            className="mx-auto text-lime-600 animate-pulse mb-3"
          />
          <p className="text-sm font-medium text-zinc-700">
            면접 질문 생성 중...
          </p>
          <p className="text-xs text-zinc-400 mt-1">
            6개 카테고리 × {qPerCategory}개 = 최대 {6 * qPerCategory}개 질문
          </p>
        </div>
      )}

      {result && !loading && (
        <div className="flex flex-col gap-4">
          {result.excluded_categories &&
            result.excluded_categories.length > 0 && (
              <div className="bg-zinc-50 border border-zinc-200 rounded-xl px-4 py-3 text-sm text-zinc-600">
                데이터 부족으로 제외된 카테고리:{" "}
                {result.excluded_categories.join(", ")}
              </div>
            )}

          {/* 요약 */}
          <div className="bg-white border border-zinc-200 rounded-xl px-5 py-4 flex items-center justify-between">
            <p className="text-sm text-zinc-700">
              총{" "}
              <b className="text-zinc-900 text-base">
                {result.questions.length}
              </b>
              개 면접 질문 생성됨
            </p>
            <div className="flex gap-1.5">
              {Object.keys(byCategory).map((cat) => {
                const [emoji] = CATEGORY_LABELS[cat] ?? ["❓"];
                return (
                  <span key={cat} className="text-base" title={cat}>
                    {emoji}
                  </span>
                );
              })}
            </div>
          </div>

          {/* 카테고리별 */}
          {Object.entries(byCategory).map(([cat, qs]) => (
            <CategoryAccordion key={cat} category={cat} questions={qs} />
          ))}

          {/* 약점 영역 */}
          {result.weak_areas && result.weak_areas.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-amber-900 mb-2">
                ⚠️ 집중 준비 영역
              </h3>
              {result.weak_areas.map((area, i) => (
                <p key={i} className="text-sm text-amber-800 leading-relaxed">
                  · {area}
                </p>
              ))}
            </div>
          )}

          {/* 예시 답변 */}
          {result.sample_answers && result.sample_answers.length > 0 && (
            <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-zinc-100">
                <h3 className="text-sm font-semibold text-zinc-800">
                  예시 답변
                </h3>
              </div>
              <div className="divide-y divide-zinc-100">
                {result.sample_answers.map((sa, i) => (
                  <details key={i} className="group">
                    <summary className="flex items-center gap-2 px-5 py-3.5 cursor-pointer hover:bg-zinc-50 transition-colors list-none">
                      <ChevronDown
                        size={13}
                        className="text-zinc-400 group-open:rotate-180 transition-transform shrink-0"
                      />
                      <span className="text-sm text-zinc-800">
                        💬 {sa.question}
                      </span>
                    </summary>
                    <div className="px-5 pb-4 pt-1 text-sm text-zinc-700 bg-zinc-50/50 whitespace-pre-wrap leading-relaxed">
                      {sa.answer}
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
