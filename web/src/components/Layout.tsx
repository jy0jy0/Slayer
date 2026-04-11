import { useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../supabaseClient'
import {
  Sword, LayoutDashboard, Building2, BarChart2, Sparkles,
  PenLine, MessageCircleQuestion, Mail, LogOut, ChevronRight
} from 'lucide-react'
import { AppProvider, useAppContext } from '../context/AppContext'
import DashboardPage from '../pages/DashboardPage'
import CompanyResearchPage from '../pages/CompanyResearchPage'
import JDMatchPage from '../pages/JDMatchPage'
import OptimizePage from '../pages/OptimizePage'
import CoverLetterPage from '../pages/CoverLetterPage'
import InterviewPrepPage from '../pages/InterviewPrepPage'
import GmailMonitorPage from '../pages/GmailMonitorPage'

export type PageKey = LayoutPageKey

export type LayoutPageKey =
  | 'dashboard'
  | 'company-research'
  | 'jd-match'
  | 'optimize'
  | 'cover-letter'
  | 'interview-prep'
  | 'gmail-monitor'

interface NavItemDef {
  key: LayoutPageKey
  icon: React.ReactNode
  label: string
  section?: 'main' | 'workflow' | 'monitor'
}

const NAV_ITEMS: NavItemDef[] = [
  { key: 'dashboard',        icon: <LayoutDashboard size={15} />,       label: '지원 현황',    section: 'main' },
  { key: 'company-research', icon: <Building2 size={15} />,             label: 'Company Research', section: 'workflow' },
  { key: 'jd-match',         icon: <BarChart2 size={15} />,             label: 'JD Match',     section: 'workflow' },
  { key: 'optimize',         icon: <Sparkles size={15} />,              label: 'Resume Optimize', section: 'workflow' },
  { key: 'cover-letter',     icon: <PenLine size={15} />,               label: 'Cover Letter', section: 'workflow' },
  { key: 'interview-prep',   icon: <MessageCircleQuestion size={15} />, label: 'Interview Prep', section: 'workflow' },
  { key: 'gmail-monitor',    icon: <Mail size={15} />,                  label: 'Gmail Monitor', section: 'monitor' },
]

const SECTION_LABELS = {
  main: null,
  workflow: 'AI 워크플로우',
  monitor: '모니터링',
}

interface SidebarProps {
  page: PageKey
  setPage: (p: PageKey) => void
  session: Session
}

function Sidebar({ page, setPage, session }: SidebarProps) {
  const user = session.user
  const meta = user.user_metadata as Record<string, string>
  const displayName = meta.full_name || user.email || '?'
  const { jd, resume, matchResult, companyResearch } = useAppContext()

  // 각 워크플로우 아이템의 데이터 준비 상태
  const readyMap: Partial<Record<PageKey, boolean>> = {
    'jd-match':       !!(jd || resume),
    'optimize':       !!matchResult,
    'cover-letter':   !!(resume && jd),
    'interview-prep': !!(resume && jd),
    'company-research': !!companyResearch,
  }

  const sections = ['main', 'workflow', 'monitor'] as const
  const grouped = sections.map(sec => ({
    sec,
    label: SECTION_LABELS[sec],
    items: NAV_ITEMS.filter(n => n.section === sec),
  }))

  return (
    <aside className="w-48 shrink-0 bg-white border-r border-zinc-200 flex flex-col h-screen sticky top-0">
      {/* 로고 */}
      <div className="h-13 flex items-center gap-2.5 px-4 py-3.5 border-b border-zinc-100">
        <div className="w-7 h-7 rounded-lg bg-lime-600 flex items-center justify-center shadow-sm">
          <Sword size={14} className="text-white" />
        </div>
        <div>
          <div className="text-sm font-bold text-zinc-900 leading-none tracking-tight">Slayer</div>
          <div className="text-[10px] text-zinc-400 mt-0.5 tracking-widest uppercase">Career AI</div>
        </div>
      </div>

      {/* 네비게이션 */}
      <nav className="flex-1 py-3 px-2 overflow-y-auto flex flex-col gap-4">
        {grouped.map(({ sec, label, items }) => (
          <div key={sec}>
            {label && (
              <div className="px-2 mb-1">
                <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-widest">
                  {label}
                </span>
              </div>
            )}
            <div className="flex flex-col gap-0.5">
              {items.map(item => {
                const isActive = page === item.key
                const isReady = readyMap[item.key]
                return (
                  <button
                    key={item.key}
                    onClick={() => setPage(item.key)}
                    className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs transition-all text-left group ${
                      isActive
                        ? 'bg-lime-600 text-white shadow-sm'
                        : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900'
                    }`}
                  >
                    <span className={`shrink-0 ${isActive ? 'text-white' : 'text-zinc-400 group-hover:text-zinc-600'}`}>
                      {item.icon}
                    </span>
                    <span className="flex-1 font-medium">{item.label}</span>
                    {isReady && !isActive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-lime-500 shrink-0" title="데이터 준비됨" />
                    )}
                    {isActive && <ChevronRight size={11} className="text-white/70 shrink-0" />}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* 파이프라인 현황 */}
      <div className="px-3 py-2 border-t border-zinc-100">
        <div className="flex gap-1 flex-wrap mb-2">
          {[
            { label: 'JD', ready: !!jd },
            { label: '이력서', ready: !!resume },
            { label: '매칭', ready: !!matchResult },
            { label: '리서치', ready: !!companyResearch },
          ].map(({ label, ready }) => (
            <span
              key={label}
              className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                ready
                  ? 'bg-lime-50 text-lime-700 border border-lime-200'
                  : 'bg-zinc-100 text-zinc-400 border border-zinc-200'
              }`}
            >
              {ready ? '✓' : '○'} {label}
            </span>
          ))}
        </div>
      </div>

      {/* 유저 */}
      <div className="p-2 border-t border-zinc-100">
        <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
          {meta.avatar_url ? (
            <img src={meta.avatar_url} alt="avatar" className="w-6 h-6 rounded-full" />
          ) : (
            <div className="w-6 h-6 rounded-full bg-lime-100 flex items-center justify-center text-xs font-bold text-lime-700">
              {displayName[0].toUpperCase()}
            </div>
          )}
          <span className="text-xs text-zinc-600 truncate flex-1 min-w-0">{displayName}</span>
        </div>
        <button
          onClick={() => supabase.auth.signOut()}
          className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-zinc-400
            hover:bg-zinc-100 hover:text-zinc-700 transition-colors"
        >
          <LogOut size={12} />
          로그아웃
        </button>
      </div>
    </aside>
  )
}

interface LayoutInnerProps {
  session: Session
}

function LayoutInner({ session }: LayoutInnerProps) {
  const [page, setPage] = useState<PageKey>('dashboard')
  const userId = session.user.id

  const renderPage = () => {
    switch (page) {
      case 'dashboard':        return <DashboardPage session={session} />
      case 'company-research': return <CompanyResearchPage onNavigate={setPage} />
      case 'jd-match':         return <JDMatchPage userId={userId} onNavigate={setPage} />
      case 'optimize':         return <OptimizePage onNavigate={setPage} />
      case 'cover-letter':     return <CoverLetterPage onNavigate={setPage} />
      case 'interview-prep':   return <InterviewPrepPage onNavigate={setPage} />
      case 'gmail-monitor':    return <GmailMonitorPage userId={userId} />
    }
  }

  return (
    <div className="min-h-screen flex bg-zinc-50">
      <Sidebar page={page} setPage={setPage} session={session} />
      <main className="flex-1 overflow-auto min-w-0 h-screen">
        {renderPage()}
      </main>
    </div>
  )
}

interface Props {
  session: Session
}

export default function Layout({ session }: Props) {
  return (
    <AppProvider>
      <LayoutInner session={session} />
    </AppProvider>
  )
}
