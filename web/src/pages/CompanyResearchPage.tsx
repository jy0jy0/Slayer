import { useState } from 'react'
import { Search, Building2, TrendingUp, Newspaper, ArrowRight } from 'lucide-react'
import { runCompanyResearch } from '../services/api'
import { useAppContext } from '../context/AppContext'
import type { LayoutPageKey } from '../components/Layout'

interface Props {
  onNavigate: (page: LayoutPageKey) => void
}

export default function CompanyResearchPage({ onNavigate }: Props) {
  const { companyResearch, setCompanyResearch } = useAppContext()
  const [company, setCompany] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const result = companyResearch

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!company.trim()) return
    setError('')
    setLoading(true)
    try {
      const data = await runCompanyResearch(company.trim())
      setCompanyResearch(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '리서치 실패')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-zinc-900">Company Research</h1>
        <p className="text-sm text-zinc-500 mt-1">기업 정보, 재무 데이터, 최신 뉴스를 AI 에이전트가 자동 수집합니다.</p>
      </div>

      {/* 검색 폼 */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            value={company}
            onChange={e => setCompany(e.target.value)}
            placeholder="카카오, 삼성전자, 네이버..."
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-zinc-200 text-zinc-900
              placeholder-zinc-400 text-sm focus:outline-none focus:border-lime-500 focus:ring-2
              focus:ring-lime-100 transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !company.trim()}
          className="px-5 py-2.5 rounded-xl bg-lime-600 hover:bg-lime-700 text-white text-sm font-semibold
            transition-colors disabled:opacity-50 shrink-0"
        >
          {loading ? '수집 중...' : '리서치'}
        </button>
      </form>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600 mb-4">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-white border border-zinc-200 rounded-xl p-10 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-lime-50 border border-lime-200 mb-4">
            <Building2 size={20} className="text-lime-600 animate-pulse" />
          </div>
          <p className="text-sm font-medium text-zinc-700">AI 에이전트가 데이터를 수집하는 중...</p>
          <p className="text-xs text-zinc-400 mt-1">기업 정보 · 재무 데이터 · 뉴스를 동시에 검색합니다</p>
        </div>
      )}

      {result && !loading && (
        <div className="flex flex-col gap-4">
          {/* 헤더 + 다음 단계 */}
          <div className="bg-white border border-zinc-200 rounded-xl px-5 py-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-zinc-900">
                {result.company_name}
                {result.company_name_en && (
                  <span className="text-zinc-400 font-normal text-base ml-2">({result.company_name_en})</span>
                )}
              </h2>
              <p className="text-xs text-lime-600 mt-0.5 font-medium">✓ 리서치 완료 — 자소서/면접 준비에 활용됩니다</p>
            </div>
            <button
              onClick={() => onNavigate('jd-match')}
              className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-700
                text-white transition-colors shrink-0"
            >
              JD Match로 <ArrowRight size={12} />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* 기본정보 */}
            {result.basic_info && (
              <div className="bg-white border border-zinc-200 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Building2 size={14} className="text-lime-600" />
                  <h3 className="text-sm font-semibold text-zinc-800">기본 정보</h3>
                </div>
                <dl className="flex flex-col gap-2.5">
                  {[
                    ['업종', result.basic_info.industry],
                    ['CEO', result.basic_info.ceo],
                    ['직원 수', result.basic_info.employee_count],
                    ['본사', result.basic_info.headquarters],
                    ['설립일', result.basic_info.founded_date],
                    ['상장', result.basic_info.listing_info],
                  ].filter(([, v]) => v).map(([k, v]) => (
                    <div key={k as string} className="flex gap-3 text-sm">
                      <dt className="text-zinc-400 w-14 shrink-0 text-xs pt-0.5">{k}</dt>
                      <dd className="text-zinc-700 text-xs leading-relaxed">{v as string}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}

            {/* 재무정보 */}
            {result.financial_info && (
              <div className="bg-white border border-zinc-200 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp size={14} className="text-lime-600" />
                  <h3 className="text-sm font-semibold text-zinc-800">
                    재무 {result.financial_info.fiscal_year ? `(${result.financial_info.fiscal_year})` : ''}
                  </h3>
                </div>
                <dl className="flex flex-col gap-2.5">
                  {[
                    ['매출', result.financial_info.revenue],
                    ['영업이익', result.financial_info.operating_profit],
                    ['순이익', result.financial_info.net_income],
                    ['총자산', result.financial_info.total_assets],
                    ['부채비율', result.financial_info.debt_ratio != null ? `${result.financial_info.debt_ratio}%` : null],
                  ].filter(([, v]) => v).map(([k, v]) => (
                    <div key={k as string} className="flex gap-3 text-sm">
                      <dt className="text-zinc-400 w-14 shrink-0 text-xs pt-0.5">{k}</dt>
                      <dd className="text-zinc-700 text-xs">{v as string}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </div>

          {/* 요약 */}
          {result.summary && (
            <div className="bg-white border-l-4 border-lime-500 rounded-r-xl p-5">
              <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">AI 요약</h3>
              <p className="text-sm text-zinc-700 leading-relaxed">{result.summary}</p>
            </div>
          )}

          {/* 뉴스 */}
          {result.recent_news && result.recent_news.length > 0 && (
            <div className="bg-white border border-zinc-200 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Newspaper size={14} className="text-lime-600" />
                <h3 className="text-sm font-semibold text-zinc-800">최근 뉴스</h3>
                <span className="text-xs text-zinc-400 ml-auto">{result.recent_news.length}건</span>
              </div>
              <div className="flex flex-col divide-y divide-zinc-100">
                {result.recent_news.map((news, i) => (
                  <div key={i} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex items-start justify-between gap-3">
                      {news.url ? (
                        <a href={news.url} target="_blank" rel="noopener noreferrer"
                          className="text-sm font-medium text-zinc-900 hover:text-lime-700 transition-colors leading-snug">
                          {news.title}
                        </a>
                      ) : (
                        <span className="text-sm font-medium text-zinc-900 leading-snug">{news.title}</span>
                      )}
                      {news.published_date && (
                        <span className="text-xs text-zinc-400 shrink-0 mt-0.5">{news.published_date}</span>
                      )}
                    </div>
                    {news.summary && (
                      <p className="text-xs text-zinc-500 mt-1 leading-relaxed">{news.summary}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!result && !loading && (
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-zinc-100 mb-4">
            <Building2 size={24} className="text-zinc-400" />
          </div>
          <p className="text-sm text-zinc-500">회사명을 입력하고 리서치를 시작하세요.</p>
          <p className="text-xs text-zinc-400 mt-1">수집된 정보는 자소서 · 면접 준비에 자동 활용됩니다.</p>
        </div>
      )}
    </div>
  )
}
