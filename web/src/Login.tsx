import { useState } from 'react'
import { supabase } from './supabaseClient'
import { Sword } from 'lucide-react'

const GoogleLogo = () => (
  <svg width="16" height="16" viewBox="0 0 48 48">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
    <path fill="#FBBC05" d="M10.53 28.59a14.5 14.5 0 0 1 0-9.18l-7.98-6.19a24.0 24.0 0 0 0 0 21.56l7.98-6.19z"/>
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
  </svg>
)

type Mode = 'login' | 'signup' | 'reset'

export default function Login() {
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const handleGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        scopes: 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar',
        queryParams: { access_type: 'offline', prompt: 'consent' },
      },
    })
    if (error) setError(error.message)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)

    if (mode === 'login') {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) setError(error.message)
    } else if (mode === 'signup') {
      const { error } = await supabase.auth.signUp({ email, password })
      if (error) setError(error.message)
      else setMessage('가입 완료! 이메일을 확인하거나 바로 로그인해주세요.')
    } else {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}`,
      })
      if (error) setError(error.message)
      else setMessage('비밀번호 재설정 이메일을 보냈습니다.')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* 로고 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-lime-50 border border-lime-200 mb-4">
            <Sword size={24} className="text-lime-600" />
          </div>
          <h1 className="text-2xl font-bold text-zinc-900">Slayer AI</h1>
          <p className="text-sm text-zinc-500 mt-1">AI-powered Career Command</p>
        </div>

        <div className="bg-white border border-zinc-200 rounded-2xl p-6 shadow-sm">
          {/* Google 로그인 */}
          <button
            onClick={handleGoogle}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl
              bg-white border border-zinc-200 text-zinc-700 text-sm font-medium
              hover:bg-zinc-50 hover:border-zinc-300 transition-all mb-4 shadow-sm"
          >
            <GoogleLogo />
            Google로 로그인
          </button>

          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px bg-zinc-200" />
            <span className="text-xs text-zinc-400">또는</span>
            <div className="flex-1 h-px bg-zinc-200" />
          </div>

          {/* 탭 */}
          <div className="flex rounded-xl bg-zinc-100 p-1 mb-4 text-xs">
            {(['login', 'signup', 'reset'] as Mode[]).map(m => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(''); setMessage('') }}
                className={`flex-1 py-1.5 rounded-lg font-medium transition-all ${
                  mode === m
                    ? 'bg-white text-zinc-900 shadow-sm'
                    : 'text-zinc-500 hover:text-zinc-700'
                }`}
              >
                {m === 'login' ? '로그인' : m === 'signup' ? '회원가입' : '비밀번호 재설정'}
              </button>
            ))}
          </div>

          {/* 폼 */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <input
              type="email"
              placeholder="이메일"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="px-4 py-3 rounded-xl border border-zinc-200 text-zinc-900
                placeholder-zinc-400 text-sm focus:outline-none focus:border-lime-500
                focus:ring-2 focus:ring-lime-100 transition-colors"
            />
            {mode !== 'reset' && (
              <input
                type="password"
                placeholder="비밀번호 (6자 이상)"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={6}
                className="px-4 py-3 rounded-xl border border-zinc-200 text-zinc-900
                  placeholder-zinc-400 text-sm focus:outline-none focus:border-lime-500
                  focus:ring-2 focus:ring-lime-100 transition-colors"
              />
            )}

            {error && <p className="text-xs text-red-500">{error}</p>}
            {message && <p className="text-xs text-lime-600">{message}</p>}

            <button
              type="submit"
              disabled={loading}
              className="py-3 rounded-xl bg-lime-600 hover:bg-lime-700 text-white text-sm font-semibold
                transition-colors disabled:opacity-50"
            >
              {loading ? '처리 중...' : mode === 'login' ? '로그인' : mode === 'signup' ? '회원가입' : '이메일 보내기'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
