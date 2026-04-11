import { createContext, useContext, useState } from 'react'
import type {
  JDSchema, ParsedResume, MatchResult,
  CompanyResearchOutput, ResumeOptimizationOutput,
} from '../types'

interface AppState {
  jd: JDSchema | null
  setJd: (v: JDSchema | null) => void
  resume: ParsedResume | null
  setResume: (v: ParsedResume | null) => void
  matchResult: MatchResult | null
  setMatchResult: (v: MatchResult | null) => void
  companyResearch: CompanyResearchOutput | null
  setCompanyResearch: (v: CompanyResearchOutput | null) => void
  optimizeResult: ResumeOptimizationOutput | null
  setOptimizeResult: (v: ResumeOptimizationOutput | null) => void
}

const AppContext = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [jd, setJd] = useState<JDSchema | null>(null)
  const [resume, setResume] = useState<ParsedResume | null>(null)
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null)
  const [companyResearch, setCompanyResearch] = useState<CompanyResearchOutput | null>(null)
  const [optimizeResult, setOptimizeResult] = useState<ResumeOptimizationOutput | null>(null)

  return (
    <AppContext.Provider value={{
      jd, setJd,
      resume, setResume,
      matchResult, setMatchResult,
      companyResearch, setCompanyResearch,
      optimizeResult, setOptimizeResult,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useAppContext must be used within AppProvider')
  return ctx
}
