import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/AuthProvider'
import { Shield, AlertCircle, MailCheck, Mail, Calculator } from 'lucide-react'
import { api, authApi } from '@/api'

type LoginPageStep = 'credentials' | 'challenge' | 'granted'

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
  const [granting, setGranting] = useState(false)

  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    setMounted(true)
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
      setStep('granted')
      setGranting(true)
      setTimeout(() => navigate('/dashboard'), 850)
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
    <div className="login-bg flex min-h-screen items-center justify-center px-4">
      {/* Access Granted overlay — single deliberate moment, not looping */}
      {granting && (
        <div className="access-granted-overlay">
          <div className="text-center">
            <p className="text-dossier font-mono text-lg tracking-[0.3em] uppercase font-bold">
              Access Granted
            </p>
            <p className="mt-2 text-gray-500 font-mono text-xs tracking-widest">
              Initializing workspace…
            </p>
          </div>
        </div>
      )}
      <div className={`w-full max-w-sm transition-all duration-300 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-lg bg-dossier text-charcoal">
            <Shield className="h-7 w-7" />
          </div>
          <h1 className="text-xl font-extrabold text-white tracking-wider font-mono">
            TRACE-NET
          </h1>
          <p className="mt-1 text-xs text-gray-400 font-mono uppercase tracking-[0.15em]">
            Investigation Intelligence Platform
          </p>
        </div>

        {/* Card */}
        <div className="card-glass shadow-xl">
          {step === 'credentials' ? (
            <form onSubmit={handleCredentialsSubmit} className="space-y-4" key="credentials">
              {error && (
                <div className={`alert-enter flex items-start gap-2 rounded p-3 text-sm ${
                  errorCode === 'EMAIL_NOT_VERIFIED'
                    ? 'bg-dossier/10 text-dossier-dim border border-dossier/20'
                    : errorCode === 'ACCOUNT_INACTIVE'
                    ? 'bg-gray-100 text-gray-600 border border-mist-dark'
                    : 'bg-alert/10 text-alert border border-alert/20'
                }`}>
                  {errorCode === 'EMAIL_NOT_VERIFIED' ? (
                    <MailCheck className="h-4 w-4 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  )}
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-1">
                <label className="block text-label text-gray-500">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input-field font-mono"
                  required
                  autoFocus
                  autoComplete="username"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-label text-gray-500">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field font-mono"
                  required
                  autoComplete="current-password"
                />
              </div>

              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-charcoal border-t-transparent" />
                    Authenticating...
                  </span>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>
          ) : (
            <div key="challenge">
              <div className="text-center mb-4">
                <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded bg-dossier/10 text-dossier">
                  <Calculator className="h-5 w-5" />
                </div>
                <h2 className="text-sm font-bold text-ink">Identity Verification</h2>
                <p className="mt-0.5 text-xs text-gray-500">Solve to continue</p>
              </div>

              <div className="mb-4 p-4 rounded bg-charcoal text-center border border-charcoal-light">
                <p className="text-xl font-extrabold font-mono text-dossier tracking-wider">
                  {challengeQuestion}
                </p>
                <p className="mt-2 text-[10px] text-gray-500 font-mono">
                  Expires in {Math.floor(challengeExpiresIn / 60)}m {challengeExpiresIn % 60}s
                </p>
              </div>

              <form onSubmit={handleChallengeSubmit} className="space-y-3 relative">
                {error && (
                  <div className="alert-enter flex items-start gap-2 rounded bg-alert/10 p-3 text-sm text-alert border border-alert/20">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="space-y-1">
                  <label className="block text-label text-gray-500">Answer</label>
                  <input
                    type="text"
                    name="challenge-answer"
                    className="input-field text-center text-xl tracking-[0.4em] font-mono font-bold"
                    placeholder="?"
                    required
                    autoFocus
                    inputMode="numeric"
                  />
                </div>

                {/* Scan-line overlay — visible only while verifying */}
                {loading && (
                  <div className="scan-line-overlay rounded" />
                )}

                <button type="submit" disabled={loading} className="btn-primary w-full relative overflow-hidden">
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-charcoal border-t-transparent" />
                      Verifying...
                    </span>
                  ) : (
                    'Verify'
                  )}
                </button>
              </form>

              <div className="mt-3 pt-3 border-t border-mist-dark text-center">
                <button onClick={handleBackToCredentials} className="btn-ghost text-xs">
                  ← Back to Sign In
                </button>
              </div>
            </div>
          )}

          {/* Demo accounts */}
          {step === 'credentials' && (
            <div className="mt-4 pt-4 border-t border-mist-dark">
              <p className="mb-2 text-label text-gray-400">Demo Accounts</p>
              <div className="space-y-1 text-xs text-gray-500">
                <p className="flex items-center gap-2">
                  <span className="status-dot status-dot-critical" />
                  <span className="font-mono font-semibold text-ink">admin</span>
                  <span className="text-gray-400">/</span>
                  <span className="font-mono">admin123</span>
                  <span className="text-gray-400 ml-auto">Admin</span>
                </p>
                <p className="flex items-center gap-2">
                  <span className="status-dot bg-crosscase" />
                  <span className="font-mono font-semibold text-ink">investigator</span>
                  <span className="text-gray-400">/</span>
                  <span className="font-mono">investigator123</span>
                  <span className="text-gray-400 ml-auto">Investigator</span>
                </p>
                <p className="flex items-center gap-2">
                  <span className="status-dot status-dot-active" />
                  <span className="font-mono font-semibold text-ink">analyst</span>
                  <span className="text-gray-400">/</span>
                  <span className="font-mono">analyst123</span>
                  <span className="text-gray-400 ml-auto">Analyst</span>
                </p>
              </div>
            </div>
          )}

          {/* Email verification resend */}
          {errorCode === 'EMAIL_NOT_VERIFIED' && (
            <div className="mt-4 pt-4 border-t border-mist-dark">
              <form onSubmit={handleResendVerification} className="space-y-2">
                <p className="text-label text-gray-400 flex items-center gap-1.5">
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

        <p className="mt-4 text-center text-[10px] text-gray-600 font-mono">
          Synthetic data only · Not for production use
        </p>
      </div>
    </div>
  )
}
