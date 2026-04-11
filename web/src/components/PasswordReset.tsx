import { useState } from 'react'
import { supabase } from '../supabaseClient'
import { Sword, Eye, EyeOff } from 'lucide-react'

interface Props {
  onDone: () => void
}

export default function PasswordReset({ onDone }: Props) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (password !== confirm) {
      setError('비밀번호가 일치하지 않습니다.')
      return
    }
    if (password.length < 6) {
      setError('비밀번호는 6자 이상이어야 합니다.')
      return
    }
    setLoading(true)
    const { error } = await supabase.auth.updateUser({ password })
    setLoading(false)
    if (error) {
      setError(error.message)
    } else {
      onDone()
    }
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-lime-50 border border-lime-200 mb-4">
            <Sword size={24} className="text-lime-600" />
          </div>
          <h1 className="text-2xl font-bold text-zinc-900">새 비밀번호 설정</h1>
          <p className="text-sm text-zinc-500 mt-1">새로운 비밀번호를 입력해주세요.</p>
        </div>

        <div className="bg-white border border-zinc-200 rounded-2xl p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                placeholder="새 비밀번호 (6자 이상)"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={6}
                className="w-full px-4 py-3 pr-11 rounded-xl border border-zinc-200 text-zinc-900
                  placeholder-zinc-400 text-sm focus:outline-none focus:border-lime-500 focus:ring-2
                  focus:ring-lime-100 transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
              >
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <input
              type={showPw ? 'text' : 'password'}
              placeholder="비밀번호 확인"
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              required
              className="px-4 py-3 rounded-xl border border-zinc-200 text-zinc-900
                placeholder-zinc-400 text-sm focus:outline-none focus:border-lime-500 focus:ring-2
                focus:ring-lime-100 transition-colors"
            />

            {error && <p className="text-xs text-red-500">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="py-3 rounded-xl bg-lime-600 hover:bg-lime-700 text-white text-sm font-semibold
                transition-colors disabled:opacity-50"
            >
              {loading ? '저장 중...' : '비밀번호 저장'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
