import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/AuthProvider'
import { Shield, AlertCircle, MailCheck, Mail, Calculator } from 'lucide-react'
import { api, authApi } from '@/api'

type LoginPageStep = 'credentials' | 'challenge'

function FloatingParticles() {
  const particles = useMemo(() =>
    Array.from({ length: 25 }, (_, i) => ({
      id: i,
      left: `${Math.random() * 100}%`,
      size: Math.random() * 5 + 2,
      duration: Math.random() * 18 + 12,
      delay: Math.random() * 12,
      opacity: Math.random() * 0.5 + 0.15,
    })), [])

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => (
        <div
          key={p.id}
          className="particle"
          style={{
            left: p.left,
            width: p.size,
            height: p.size,
            opacity: p.opacity,
            animationDuration: `${p.duration}s`,
            animationDelay: `${p.delay}s`,
          }}
        />
      ))}
    </div>
  )
}

function FloatingOrbs() {
  return (
    <>
      <div className="absolute top-[15%] left-[10%] w-64 h-64 bg-trace-500/10 rounded-full blur-3xl pointer-events-none" style={{ animation: 'float 8s ease-in-out infinite' }} />
      <div className="absolute bottom-[20%] right-[10%] w-80 h-80 bg-indigo-500/8 rounded-full blur-3xl pointer-events-none" style={{ animation: 'float 10s ease-in-out infinite 2s' }} />
      <div className="absolute top-[60%] left-[50%] w-48 h-48 bg-purple-500/6 rounded-full blur-3xl pointer-events-none" style={{ animation: 'float 12s ease-in-out infinite 4s' }} />
    </>
  )
}

export function LoginPage() {
  const { loginWithOtp } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState<LoginPageStep>('credentials')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [challengeId, setChallengeId] = useState('')
  const [challengeQuestion, setChallengeQuestion] = useState('')
  const [challengeExpiresIn, setChallengeExpiresIn] = useState(120)
  const [error, setError] = useState('')
  const [errorCode, setErrorCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [resendEmail, setResendEmail] = useState('')
  const [resendLoading, setResendLoading] = useState(false)
  const [resendMessage, setResendMessage] = useState('')

  const [mounted, setMounted] = useState(false)
  const [cardMounted, setCardMounted] = useState(false)
  useEffect(() => {
    setMounted(true)
    setTimeout(() => setCardMounted(true), 100)
  }, [])

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setErrorCode('')
    setLoading(true)
    try {
      const { data } = await authApi.login(username, password)
      if (data.requires_challenge) {
        setChallengeId(data.challenge_id)
        setChallengeQuestion(data.question)
        setChallengeExpiresIn(data.expires_in_seconds || 120)
        setStep('challenge')
        setError('')
      }
    } catch (err: any) {
      const status = err.response?.status
      const authError = err.response?.headers?.['x-auth-error'] || ''
      setErrorCode(authError)
      if (authError === 'EMAIL_NOT_VERIFIED' || status === 403) {
        setError('Your email has not been verified yet. Please verify your email before signing in.')
      } else if (authError === 'ACCOUNT_INACTIVE') {
        setError('This account is currently inactive. Contact an administrator.')
      } else if (status === 429) {
        setError('Too many login attempts. Please try again later.')
      } else if (status === 401) {
        setError('Incorrect username or password.')
      } else {
        setError('Unable to connect to the server. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleChallengeSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const form = e.target as HTMLFormElement
      const answerInput = form.querySelector('input[name="challenge-answer"]') as HTMLInputElement
      const answer = answerInput?.value || ''
      const { data } = await authApi.verifyChallenge(challengeId, answer)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      loginWithOtp(data.user)
      navigate('/dashboard')
    } catch (err: any) {
      const detail = err.response?.data?.detail || ''
      const challStatus = err.response?.status
      if (detail.includes('expired')) {
        setError('This challenge has expired. Please go back and log in again.')
      } else if (detail.includes('already been used')) {
        setError('This challenge has already been used. Please go back and log in again.')
      } else if (detail.includes('attempts remaining')) {
        setError(detail)
      } else if (detail.includes('Too many incorrect')) {
        setError('Too many incorrect attempts. Please go back and log in again.')
      } else if (challStatus === 429) {
        setError('Too many requests. Please try again later.')
      } else {
        setError(detail || 'Invalid answer. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleBackToCredentials = () => {
    setStep('credentials')
    setError('')
    setChallengeId('')
    setChallengeQuestion('')
  }

  const handleResendVerification = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resendEmail.trim()) return
    setResendLoading(true)
    setResendMessage('')
    try {
      await api.post('/auth/verify-email/request', { email: resendEmail })
      setResendMessage('If the account exists, a verification email has been sent.')
    } catch {
      setResendMessage('An error occurred. Please try again.')
    } finally {
      setResendLoading(false)
    }
  }

  return (
    <div className="login-bg flex min-h-screen items-center justify-center px-4 relative">
      <FloatingParticles />
      <FloatingOrbs />

      <div className={`w-full max-w-md transition-all duration-700 ease-out ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}`}>
        {/* Logo */}
        <div className="mb-10 text-center">
          <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-trace-500 via-indigo-500 to-purple-600 shadow-2xl shield-glow">
            <Shield className="h-11 w-11 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight" style={{ textShadow: '0 0 40px rgba(99, 102, 241, 0.3)' }}>
            TRACE-NET
          </h1>
          <p className="mt-1.5 text-sm text-indigo-200/60 font-medium">Investigation Intelligence Platform</p>
        </div>

        {/* Card */}
        <div className={`card-glass shadow-2xl transition-all duration-500 ease-out ${cardMounted ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-6 scale-95'}`}>
          {step === 'credentials' ? (
            <form onSubmit={handleCredentialsSubmit} className="space-y-5" key="credentials">
              {error && (
                <div className={`alert-enter flex items-start gap-2.5 rounded-xl p-3.5 text-sm ${
                  errorCode === 'EMAIL_NOT_VERIFIED'
                    ? 'bg-amber-50/80 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border border-amber-200/50'
                    : errorCode === 'ACCOUNT_INACTIVE'
                    ? 'bg-gray-50/80 dark:bg-gray-800/50 text-gray-700 dark:text-gray-400 border border-gray-200/50'
                    : 'bg-red-50/80 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200/50'
                }`}>
                  {errorCode === 'EMAIL_NOT_VERIFIED' ? (
                    <MailCheck className="h-4 w-4 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  )}
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input-field"
                  required
                  autoFocus
                  autoComplete="username"
                />
              </div>

              <div className="space-y-1.5">
                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field"
                  required
                  autoComplete="current-password"
                />
              </div>

              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Signing in...
                  </span>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>
          ) : (
            <div key="challenge">
              <div className="text-center mb-5">
                <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-trace-500 to-indigo-600 shadow-lg" style={{ animation: 'float 3s ease-in-out infinite' }}>
                  <Calculator className="h-7 w-7 text-white" />
                </div>
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">Verify Your Identity</h2>
                <p className="mt-1 text-sm text-gray-500">Solve this simple challenge to continue</p>
              </div>

              <div className="mb-5 p-5 rounded-xl text-center" style={{ background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.06) 100%)', border: '1px solid rgba(99, 102, 241, 0.15)' }}>
                <p className="text-2xl font-extrabold text-trace-700 dark:text-trace-300" style={{ animation: 'neon-pulse 2s ease-in-out infinite' }}>
                  {challengeQuestion}
                </p>
                <p className="mt-2 text-xs text-gray-500">
                  Expires in {Math.floor(challengeExpiresIn / 60)}m {challengeExpiresIn % 60}s
                </p>
              </div>

              <form onSubmit={handleChallengeSubmit} className="space-y-4">
                {error && (
                  <div className="alert-enter flex items-start gap-2.5 rounded-xl bg-red-50/80 dark:bg-red-900/20 p-3.5 text-sm text-red-700 dark:text-red-400 border border-red-200/50">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">Your Answer</label>
                  <input
                    type="text"
                    name="challenge-answer"
                    className="input-field text-center text-2xl tracking-[0.3em] font-mono font-bold"
                    placeholder="?"
                    required
                    autoFocus
                    inputMode="numeric"
                  />
                </div>

                <button type="submit" disabled={loading} className="btn-primary w-full">
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Verifying...
                    </span>
                  ) : (
                    'Submit Answer'
                  )}
                </button>
              </form>

              <div className="mt-4 border-t border-gray-200/50 dark:border-gray-700/50 pt-4 text-center">
                <button onClick={handleBackToCredentials} className="btn-ghost text-sm">
                  ← Back to Sign In
                </button>
              </div>
            </div>
          )}

          {/* Demo accounts */}
          {step === 'credentials' && (
            <div className="mt-6 border-t border-gray-200/50 dark:border-gray-700/50 pt-5">
              <p className="mb-2.5 text-[10px] font-bold text-gray-400 uppercase tracking-widest">Demo Accounts</p>
              <div className="space-y-1.5 text-xs text-gray-500 dark:text-gray-400">
                <p className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  <span className="font-mono font-semibold text-gray-700 dark:text-gray-300">admin</span> / <span className="font-mono">admin123</span>
                  <span className="text-gray-400">— Admin</span>
                </p>
                <p className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                  <span className="font-mono font-semibold text-gray-700 dark:text-gray-300">investigator</span> / <span className="font-mono">investigator123</span>
                  <span className="text-gray-400">— Investigator</span>
                </p>
                <p className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  <span className="font-mono font-semibold text-gray-700 dark:text-gray-300">analyst</span> / <span className="font-mono">analyst123</span>
                  <span className="text-gray-400">— Analyst</span>
                </p>
              </div>
            </div>
          )}

          {/* Email verification resend */}
          {errorCode === 'EMAIL_NOT_VERIFIED' && (
            <div className="mt-5 border-t border-gray-200/50 dark:border-gray-700/50 pt-5">
              <form onSubmit={handleResendVerification} className="space-y-3">
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
                  <Mail className="h-3 w-3" /> Resend Verification
                </p>
                <input
                  type="email"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="input-field text-sm"
                  required
                />
                <button type="submit" disabled={resendLoading} className="btn-secondary w-full text-sm">
                  {resendLoading ? 'Sending...' : 'Send Verification Email'}
                </button>
              </form>
              {resendMessage && (
                <p className="mt-2 text-xs text-gray-500">{resendMessage}</p>
              )}
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-[11px] text-indigo-300/30 font-medium">
          Prototype using synthetic data. Not for production use.
        </p>
      </div>
    </div>
  )
}
