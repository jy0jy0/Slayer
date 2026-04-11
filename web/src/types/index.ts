// ─── Application / Kanban ─────────────────────────────────────────────────────

export type AppStatus =
  | 'scrapped'
  | 'reviewing'
  | 'applied'
  | 'in_progress'
  | 'final_pass'
  | 'rejected'
  | 'withdrawn'

export interface Application {
  application_id: string
  company: string | null
  status: AppStatus
  ats_score: number | null
  applied_at: string | null
  deadline: string | null
  created_at: string | null
}

export interface GmailEvent {
  id: string
  company: string | null
  status_type: 'PASS' | 'FAIL' | 'INTERVIEW' | 'REJECT' | null
  stage: string | null
  summary: string | null
  subject: string | null
  received_at: string | null
}

export const STATUS_META: Record<AppStatus, { label: string; color: string; border: string }> = {
  scrapped:    { label: '스크랩',   color: '#6b7280', border: 'border-l-[#6b7280]' },
  reviewing:   { label: '검토중',   color: '#3b82f6', border: 'border-l-[#3b82f6]' },
  applied:     { label: '지원완료', color: '#8b5cf6', border: 'border-l-[#8b5cf6]' },
  in_progress: { label: '전형중',   color: '#f59e0b', border: 'border-l-[#f59e0b]' },
  final_pass:  { label: '최종합격', color: '#10b981', border: 'border-l-[#10b981]' },
  rejected:    { label: '불합격',   color: '#ef4444', border: 'border-l-[#ef4444]' },
  withdrawn:   { label: '취소',     color: '#6b7280', border: 'border-l-[#6b7280]' },
}

export const BOARD_COLUMNS: AppStatus[] = [
  'scrapped', 'reviewing', 'applied', 'in_progress', 'final_pass', 'rejected',
]

// ─── Company Research ────────────────────────────────────────────────────────

export interface BasicInfo {
  industry?: string | null
  ceo?: string | null
  employee_count?: string | null
  headquarters?: string | null
  founded_date?: string | null
  listing_info?: string | null
}

export interface FinancialInfo {
  fiscal_year?: string | null
  revenue?: string | null
  operating_profit?: string | null
  net_income?: string | null
  total_assets?: string | null
  debt_ratio?: number | null
}

export interface NewsArticle {
  title: string
  url?: string | null
  published_date?: string | null
  source?: string | null
  summary?: string | null
}

export interface CompanyResearchOutput {
  company_name: string
  company_name_en?: string | null
  basic_info?: BasicInfo | null
  financial_info?: FinancialInfo | null
  recent_news?: NewsArticle[]
  summary?: string | null
}

// ─── JD / Resume / Match ─────────────────────────────────────────────────────

export interface JDSchema {
  company?: string | null
  title?: string | null
  position?: string | null
  requirements?: string[]
  skills?: string[]
  [key: string]: unknown
}

export interface PersonalInfo {
  name?: string | null
  email?: string | null
  phone?: string | null
}

export interface ParsedResume {
  personal_info?: PersonalInfo | null
  skills?: string[]
  experiences?: unknown[]
  projects?: unknown[]
  summary?: string | null
  total_years_experience?: number | null
  source_format?: string | null
  [key: string]: unknown
}

export interface MatchResult {
  ats_score: number
  matched_keywords: string[]
  missing_keywords: string[]
  strengths: string[]
  weaknesses: string[]
  gap_summary?: string | null
  score_breakdown?: Record<string, number> | null
}

// ─── Resume Optimize ─────────────────────────────────────────────────────────

export interface OptimizeInput {
  parsed_resume: ParsedResume
  jd: JDSchema
  match_result: MatchResult
  target_ats_score?: number
  max_iterations?: number
}

export interface ResumeChange {
  block_type?: string
  field?: string
  before?: string
  after?: string
  reason?: string
}

export interface ResumeOptimizationOutput {
  final_ats_score: number
  score_improvement: number
  iterations_used: number
  optimization_summary?: string | null
  changes?: ResumeChange[]
  optimized_blocks?: unknown[]
}

// ─── Cover Letter ─────────────────────────────────────────────────────────────

export interface CoverLetterInput {
  parsed_resume: ParsedResume
  jd: JDSchema
  company_research?: CompanyResearchOutput | null
  match_result?: MatchResult | null
}

export interface CoverLetterOutput {
  cover_letter: string
  word_count: number
  jd_keyword_coverage: number
  key_points?: string[]
}

// ─── Interview Prep ───────────────────────────────────────────────────────────

export interface InterviewInput {
  jd: JDSchema
  resume: ParsedResume
  company_research?: CompanyResearchOutput | null
  match_result?: MatchResult | null
  questions_per_category?: number
}

export interface InterviewQuestion {
  question: string
  category: string
  intent?: string
  tip?: string
  source?: string
}

export interface InterviewQuestionsOutput {
  questions: InterviewQuestion[]
  sample_answers?: { question: string; answer: string }[]
  weak_areas?: string[]
  excluded_categories?: string[]
}
