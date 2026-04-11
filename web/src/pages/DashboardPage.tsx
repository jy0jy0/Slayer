import { useState, useEffect, useCallback } from 'react'
import type { Session } from '@supabase/supabase-js'
import { fetchApplications, fetchGmailEvents, pollGmail } from '../services/api'
import type { Application, GmailEvent } from '../types'
import KanbanBoard from '../components/kanban/KanbanBoard'
import GmailFeed from '../components/GmailFeed'

interface Props {
  session: Session
}

export default function DashboardPage({ session }: Props) {
  const userId = session.user.id

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
    <div className="flex flex-col h-full">
      {/* 페이지 헤더 */}
      <div className="px-6 py-5 border-b border-zinc-200 bg-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-zinc-900">지원 현황</h1>
            <p className="text-xs text-zinc-500 mt-0.5">카드를 드래그해서 상태를 변경하세요</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span>총 <b className="text-zinc-900">{totalApps}</b>건</span>
            <span>전형중 <b className="text-amber-600">{inProgress}</b>건</span>
            <span>최종합격 <b className="text-emerald-600">{finalPass}</b>건</span>
          </div>
        </div>
      </div>

      {/* 메인 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 칸반 */}
        <div className="flex-1 overflow-x-auto p-6">
          <KanbanBoard apps={apps} userId={userId} onRefresh={loadApps} />
        </div>

        {/* Gmail 사이드바 */}
        <div className="border-l border-zinc-200 p-4 w-72 shrink-0 overflow-y-auto bg-white">
          <GmailFeed events={gmailEvents} onPoll={handlePoll} polling={polling} />
        </div>
      </div>
    </div>
  )
}
