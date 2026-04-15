import type {
  Application,
  AppStatus,
  GmailEvent,
  CompanyResearchOutput,
  JDSchema,
  ParsedResume,
  MatchResult,
  OptimizeInput,
  ResumeOptimizationOutput,
  CoverLetterInput,
  CoverLetterOutput,
  InterviewInput,
  InterviewQuestionsOutput,
} from "../types";

const BASE = "/api/v1";

// ──────────────────────────────────────────────────────────────────────────────
// Error helpers
// ──────────────────────────────────────────────────────────────────────────────

type ApiErrorPayload =
  | {
      detail?: unknown;
      message?: unknown;
      error?: unknown;
    }
  | undefined
  | null;

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

function stringifyUnknown(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "string") return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);

  if (Array.isArray(v)) {
    const joined = v.map(stringifyUnknown).filter(Boolean).join(" · ");
    return joined;
  }

  if (isRecord(v)) {
    // FastAPI/Pydantic validation shape
    if ("msg" in v && typeof v.msg === "string") {
      const loc = Array.isArray(v.loc) ? `(${v.loc.join(".")}) ` : "";
      return `${loc}${v.msg}`.trim();
    }
    if ("detail" in v) return stringifyUnknown(v.detail);
    if ("message" in v) return stringifyUnknown(v.message);
    if ("error" in v) return stringifyUnknown(v.error);
  }

  try {
    return JSON.stringify(v);
  } catch {
    return "";
  }
}

function normalizeApiErrorMessage(
  payload: ApiErrorPayload,
  fallback: string,
  status?: number,
): string {
  const raw =
    payload?.detail ?? payload?.message ?? payload?.error ?? payload ?? null;
  const parsed = stringifyUnknown(raw);

  const base = parsed || fallback;
  const withStatus = status ? `${base} (HTTP ${status})` : base;

  // Resume-specific friendly hints
  const lower = withStatus.toLowerCase();

  if (
    lower.includes("no text extracted") ||
    lower.includes("failed to extract text")
  ) {
    return `${withStatus}\n\n힌트: 스캔본 PDF(이미지)일 수 있어요. 텍스트가 포함된 PDF/DOCX로 다시 업로드해 보세요.`;
  }

  if (
    lower.includes("unsupported format") ||
    lower.includes("지원하지 않는 파일")
  ) {
    return `${withStatus}\n\n지원 형식: PDF, DOCX, MD, TXT, JSON`;
  }

  if (lower.includes("llm 파싱 실패") || lower.includes("llm failed")) {
    return `${withStatus}\n\n힌트: 잠시 후 다시 시도하거나 API 키 설정을 확인하세요.`;
  }

  return withStatus;
}

async function parseErrorResponse(
  res: Response,
  fallback: string,
): Promise<string> {
  let payload: ApiErrorPayload = null;

  try {
    payload = (await res.json()) as ApiErrorPayload;
  } catch {
    // ignore json parse failure
  }

  return normalizeApiErrorMessage(payload, fallback, res.status);
}

// ──────────────────────────────────────────────────────────────────────────────
// Applications
// ──────────────────────────────────────────────────────────────────────────────

export async function fetchApplications(
  userId: string,
): Promise<Application[]> {
  const res = await fetch(`${BASE}/applications?user_id=${userId}`);
  if (!res.ok) return [];
  return res.json();
}

export async function updateStatus(
  applicationId: string,
  userId: string,
  newStatus: AppStatus,
): Promise<void> {
  await fetch(
    `${BASE}/applications/${applicationId}/status?user_id=${userId}&new_status=${newStatus}`,
    { method: "PATCH" },
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Gmail
// ──────────────────────────────────────────────────────────────────────────────

export async function fetchGmailEvents(userId: string): Promise<GmailEvent[]> {
  const res = await fetch(`${BASE}/gmail/events?user_id=${userId}`);
  if (!res.ok) return [];
  return res.json();
}

export async function pollGmail(
  userId: string,
): Promise<{ processed: number }> {
  const res = await fetch(`${BASE}/gmail/poll/${userId}`, { method: "POST" });
  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, "폴링 실패"));
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────────────────────────
// Company Research
// ──────────────────────────────────────────────────────────────────────────────

export async function runCompanyResearch(
  companyName: string,
): Promise<CompanyResearchOutput> {
  const res = await fetch(`${BASE}/pipelines/company-research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_name: companyName }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, "리서치 실패"));
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────────────────────────
// JD Parse
// ──────────────────────────────────────────────────────────────────────────────

export async function parseJD(url: string): Promise<JDSchema> {
  const res = await fetch(`${BASE}/pipelines/jd/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, "JD 파싱 실패"));
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────────────────────────
// Resume Upload / Parse
// ──────────────────────────────────────────────────────────────────────────────

export async function uploadResume(
  file: File,
  userId: string,
): Promise<{ resume_id: string | null; parsed: ParsedResume }> {
  const form = new FormData();
  form.append("file", file);
  form.append("user_id", userId);

  const res = await fetch(`${BASE}/resumes/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const fallback = "이력서 파싱 실패";
    const msg = await parseErrorResponse(res, fallback);
    throw new Error(msg);
  }

  return res.json();
}

// ──────────────────────────────────────────────────────────────────────────────
// JD-Resume Match
// ──────────────────────────────────────────────────────────────────────────────

export async function runMatch(
  jd: JDSchema,
  resume: ParsedResume,
): Promise<MatchResult> {
  const res = await fetch(`${BASE}/pipelines/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd, resume }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, "매칭 실패"));
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────────────────────────
// Resume Optimize
// ──────────────────────────────────────────────────────────────────────────────

export async function runOptimize(
  input: OptimizeInput,
): Promise<ResumeOptimizationOutput> {
  const res = await fetch(`${BASE}/pipelines/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, "최적화 실패"));
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────────────────────────
// Cover Letter
// ──────────────────────────────────────────────────────────────────────────────

export async function generateCoverLetter(
  input: CoverLetterInput,
): Promise<CoverLetterOutput> {
  const res = await fetch(`${BASE}/pipelines/cover-letter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, "자소서 생성 실패"));
  }
  return res.json();
}

// ──────────────────────────────────────────────────────────────────────────────
// Interview Prep
// ──────────────────────────────────────────────────────────────────────────────

export async function generateInterviewQuestions(
  input: InterviewInput,
): Promise<InterviewQuestionsOutput> {
  const res = await fetch(`${BASE}/pipelines/interview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    throw new Error(await parseErrorResponse(res, "면접 질문 생성 실패"));
  }
  return res.json();
}
