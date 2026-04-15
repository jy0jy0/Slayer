import { useState, useEffect, useCallback } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../supabaseClient'
import { fetchApplications, fetchGmailEvents, pollGmail } from '../services/api'
import type { Application, GmailEvent } from '../types'
import KanbanBoard from './kanban/KanbanBoard'
import GmailFeed from './GmailFeed'
import { LogOut, Sword } from 'lucide-react'

interface Props {
  session: Session
}

export default function Dashboard({ session }: Props) {
  const user = session.user
  const userId = user.id
  const meta = user.user_metadata as Record<string, string>

  const [apps, setApps] = useState<Application[]>([])
  const [gmailEvents, setGmailEvents] = useState<GmailEvent[]>([])
  const [polling, setPolling] = useState(false)

  const loadApps = useCallback(async () => {
    const data = await fetchApplications(userId)
    setApps(data)
  }, [userId])

  const loadGmailEvents = useCallback(async () => {
    const data = await fetchGmailEvents(userId)
    setGmailEvents(data)
  }, [userId])

  useEffect(() => {
    loadApps()
    loadGmailEvents()
  }, [loadApps, loadGmailEvents])

  const handlePoll = async () => {
    setPolling(true)
    await pollGmail(userId)
    await Promise.all([loadApps(), loadGmailEvents()])
    setPolling(false)
  }

  const totalApps = apps.length
  const inProgress = apps.filter(a => a.status === 'in_progress').length
  const finalPass = apps.filter(a => a.status === 'final_pass').length

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      {/* 헤더 */}
      <header className="h-14 border-b border-zinc-800 flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-2">
          <Sword size={18} className="text-blue-400" />
          <span className="font-bold text-zinc-100 tracking-tight">Slayer AI</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-4 text-xs text-zinc-500">
            <span>총 <b className="text-zinc-300">{totalApps}</b>건</span>
            <span>전형중 <b className="text-amber-400">{inProgress}</b>건</span>
            <span>최종합격 <b className="text-emerald-400">{finalPass}</b>건</span>
          </div>
          <div className="w-px h-5 bg-zinc-800" />
          {meta.avatar_url ? (
            <img src={meta.avatar_url} alt="avatar" className="w-7 h-7 rounded-full" />
          ) : (
            <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold">
              {(meta.full_name || user.email || '?')[0].toUpperCase()}
            </div>
          )}
          <span className="text-sm text-zinc-400 hidden md:block">
            {meta.full_name || user.email}
          </span>
          <button
            onClick={() => supabase.auth.signOut()}
            className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300 transition-colors"
            title="로그아웃"
          >
            <LogOut size={15} />
          </button>
        </div>
      </header>

      {/* 메인 */}
      <main className="flex-1 flex overflow-hidden">
        {/* 칸반 */}
        <div className="flex-1 overflow-x-auto p-6">
          <div className="mb-5">
            <h1 className="text-xl font-bold text-zinc-100">지원 현황</h1>
            <p className="text-xs text-zinc-500 mt-0.5">카드를 드래그해서 상태를 변경하세요</p>
          </div>
          <KanbanBoard apps={apps} userId={userId} onRefresh={loadApps} />
        </div>

        {/* Gmail 사이드바 */}
        <div className="border-l border-zinc-800 p-4 w-72 shrink-0">
          <GmailFeed events={gmailEvents} onPoll={handlePoll} polling={polling} />
        </div>
      </main>
    </div>
  )
}
