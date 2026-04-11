import type {
  Application, AppStatus, GmailEvent,
  CompanyResearchOutput, JDSchema, ParsedResume, MatchResult,
  OptimizeInput, ResumeOptimizationOutput,
  CoverLetterInput, CoverLetterOutput,
  InterviewInput, InterviewQuestionsOutput,
} from '../types'

const BASE = '/api/v1'

// ─── Applications ─────────────────────────────────────────────────────────────

export async function fetchApplications(userId: string): Promise<Application[]> {
  const res = await fetch(`${BASE}/applications?user_id=${userId}`)
  if (!res.ok) return []
  return res.json()
}

export async function updateStatus(
  applicationId: string,
  userId: string,
  newStatus: AppStatus,
): Promise<void> {
  await fetch(
    `${BASE}/applications/${applicationId}/status?user_id=${userId}&new_status=${newStatus}`,
    { method: 'PATCH' },
  )
}

// ─── Gmail ───────────────────────────────────────────────────────────────────

export async function fetchGmailEvents(userId: string): Promise<GmailEvent[]> {
  const res = await fetch(`${BASE}/gmail/events?user_id=${userId}`)
  if (!res.ok) return []
  return res.json()
}

export async function pollGmail(userId: string): Promise<{ processed: number }> {
  const res = await fetch(`${BASE}/gmail/poll/${userId}`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `폴링 실패 (${res.status})`)
  }
  return res.json()
}

// ─── Company Research ─────────────────────────────────────────────────────────

export async function runCompanyResearch(companyName: string): Promise<CompanyResearchOutput> {
  const res = await fetch(`${BASE}/pipelines/company-research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company_name: companyName }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '리서치 실패')
  }
  return res.json()
}

// ─── JD Parse ────────────────────────────────────────────────────────────────

export async function parseJD(url: string): Promise<JDSchema> {
  const res = await fetch(`${BASE}/pipelines/jd/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'JD 파싱 실패')
  }
  return res.json()
}

// ─── Resume Upload ────────────────────────────────────────────────────────────

export async function uploadResume(
  file: File,
  userId: string,
): Promise<{ resume_id: string | null; parsed: ParsedResume }> {
  const form = new FormData()
  form.append('file', file)
  form.append('user_id', userId)
  const res = await fetch(`${BASE}/resumes/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '이력서 파싱 실패')
  }
  return res.json()
}

// ─── JD-Resume Match ─────────────────────────────────────────────────────────

export async function runMatch(jd: JDSchema, resume: ParsedResume): Promise<MatchResult> {
  const res = await fetch(`${BASE}/pipelines/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jd, resume }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '매칭 실패')
  }
  return res.json()
}

// ─── Resume Optimize ─────────────────────────────────────────────────────────

export async function runOptimize(input: OptimizeInput): Promise<ResumeOptimizationOutput> {
  const res = await fetch(`${BASE}/pipelines/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '최적화 실패')
  }
  return res.json()
}

// ─── Cover Letter ─────────────────────────────────────────────────────────────

export async function generateCoverLetter(input: CoverLetterInput): Promise<CoverLetterOutput> {
  const res = await fetch(`${BASE}/pipelines/cover-letter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '자소서 생성 실패')
  }
  return res.json()
}

// ─── Interview Prep ───────────────────────────────────────────────────────────

export async function generateInterviewQuestions(
  input: InterviewInput,
): Promise<InterviewQuestionsOutput> {
  const res = await fetch(`${BASE}/pipelines/interview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '면접 질문 생성 실패')
  }
  return res.json()
}
