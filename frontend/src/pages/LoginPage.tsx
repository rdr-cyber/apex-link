import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/AuthProvider'
import { AlertCircle, MailCheck, Mail, Calculator } from 'lucide-react'
import { api, authApi } from '@/api'
import pkg from '../../package.json'

type LoginPageStep = 'credentials' | 'challenge' | 'granted'

/** Static case-network constellation — real entity types, real seed counts.
 *  Decorative but honest: nodes/edges mirror what the graph view actually shows
 *  (bridge entities, a gold evidence path). No invented auth/UI chrome, no
 *  location/tracking imagery — this is the relationship graph, in depth.
 *
 *  Depth is done with CSS 3D only (perspective + preserve-3d layers): a gray
 *  edge plane behind, faint nodes split across two depth planes, and the gold
 *  bridge entities raised toward the viewer. A one-time settle-in animation
 *  gives the scene its depth; a gentle pointer tilt adds parallax (disabled
 *  under prefers-reduced-motion). No 3D library. */
function CaseConstellation() {
  const sceneRef = useRef<HTMLDivElement>(null)
  const tiltRef = useRef<HTMLDivElement>(null)
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    // Environments without matchMedia (e.g. jsdom) can't report the preference —
    // default to reduced motion, the safe choice.
    if (typeof window.matchMedia !== 'function') {
      setReducedMotion(true)
      return
    }
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReducedMotion(mq.matches)
    const onChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  // Gentle pointer tilt, rAF-throttled. Skipped entirely for reduced motion.
  useEffect(() => {
    if (reducedMotion) return
    const el = sceneRef.current
    if (!el) return
    let raf = 0
    const REST_RX = 5
    const REST_RY = -5
    const apply = (rx: number, ry: number) => {
      if (tiltRef.current) {
        tiltRef.current.style.transform = `rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg)`
      }
    }
    const onMove = (e: PointerEvent) => {
      const rect = el.getBoundingClientRect()
      const px = (e.clientX - rect.left) / rect.width - 0.5
      const py = (e.clientY - rect.top) / rect.height - 0.5
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => apply(REST_RX - py * 6, REST_RY + px * 8))
    }
    const onLeave = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => apply(REST_RX, REST_RY))
    }
    el.addEventListener('pointermove', onMove)
    el.addEventListener('pointerleave', onLeave)
    return () => {
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerleave', onLeave)
      cancelAnimationFrame(raf)
    }
  }, [reducedMotion])

  const edges: [number, number, number, number][] = [
    [110, 90, 230, 80], [230, 80, 300, 160], [300, 160, 420, 120],
    [420, 120, 460, 260], [460, 260, 400, 420], [400, 420, 310, 520],
    [310, 520, 160, 520], [160, 520, 70, 460], [70, 460, 60, 300],
    [60, 300, 110, 90], [150, 180, 230, 80], [150, 180, 60, 300],
    [330, 300, 300, 160], [330, 300, 420, 120], [330, 300, 460, 260],
    [330, 300, 400, 420], [210, 260, 150, 180], [210, 260, 330, 300],
    [255, 430, 330, 300], [255, 430, 160, 520], [255, 430, 400, 420],
    [255, 430, 70, 460],
  ]
  const bridgeEdges: [number, number, number, number][] = [
    [150, 180, 255, 430], [330, 300, 210, 260], [255, 430, 310, 520],
  ]
  // faint nodes split across two depth planes for per-node parallax
  const nodesFar = [
    { x: 60, y: 300, r: 4 }, { x: 230, y: 80, r: 5 }, { x: 420, y: 120, r: 5 },
    { x: 310, y: 520, r: 4 }, { x: 70, y: 460, r: 4 },
  ]
  const nodesNear = [
    { x: 110, y: 90, r: 4 }, { x: 300, y: 160, r: 4 }, { x: 460, y: 260, r: 4 },
    { x: 400, y: 420, r: 5 }, { x: 160, y: 520, r: 5 }, { x: 210, y: 260, r: 3 },
  ]
  const bridges = [
    { x: 150, y: 180, r: 7, label: 'PERSON' },
    { x: 330, y: 300, r: 9, label: 'ACCOUNT' },
    { x: 255, y: 430, r: 6, label: 'PHONE' },
  ]

  return (
    <div ref={sceneRef} className="h-full w-full" style={{ perspective: '1100px' }} aria-hidden>
      <div
        ref={tiltRef}
        className={`constellation-stage h-full w-full ${reducedMotion ? '' : 'constellation-settle'}`}
        onAnimationEnd={(e) => {
          // A filling animation would keep overriding the JS tilt (animations
          // outrank inline styles), so hand control back once settle finishes.
          if (e.target === e.currentTarget && e.animationName === 'constellationSettle') {
            e.currentTarget.classList.remove('constellation-settle')
          }
        }}
      >
        <div className="constellation-frame">
          {/* edge plane — everything connects behind the nodes */}
          <svg viewBox="0 0 520 560" className="constellation-layer" style={{ transform: 'translateZ(-40px)' }}>
            {edges.map(([x1, y1, x2, y2], i) => (
              <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#9CA3AF" strokeOpacity={0.22} strokeWidth={1} />
            ))}
          </svg>
          {/* distant node plane — blurred + dimmed for depth-of-field */}
          <svg
            viewBox="0 0 520 560" className="constellation-layer"
            style={{ transform: 'translateZ(-75px)', filter: 'blur(0.6px)', opacity: 0.6 }}
          >
            {nodesFar.map((n, i) => (
              <circle key={i} cx={n.x} cy={n.y} r={n.r} fill="#9CA3AF" fillOpacity={0.5} />
            ))}
          </svg>
          {/* near plane — remaining nodes + the gold evidence path */}
          <svg viewBox="0 0 520 560" className="constellation-layer" style={{ transform: 'translateZ(-10px)' }}>
            {nodesNear.map((n, i) => (
              <circle key={i} cx={n.x} cy={n.y} r={n.r} fill="#9CA3AF" fillOpacity={0.5} />
            ))}
            {bridgeEdges.map(([x1, y1, x2, y2], i) => (
              <line key={`b${i}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#D4A853" strokeOpacity={0.4} strokeWidth={1} />
            ))}
            {/* gold evidence path — the app's real path-finder motif */}
            <polyline
              points="110,90 150,180 210,260 330,300"
              fill="none" stroke="#D4A853" strokeOpacity={0.6}
              strokeWidth={1.5} strokeDasharray="5 5"
            />
          </svg>
          {/* bridge entities — raised toward the viewer, gold ring + label */}
          {bridges.map((n) => (
            <div
              key={n.label}
              className="constellation-bridge"
              style={{
                left: `${(n.x / 520) * 100}%`,
                top: `${(n.y / 560) * 100}%`,
                width: (n.r + 6) * 2,
                height: (n.r + 6) * 2,
                transform: `translate(-50%, -50%) translateZ(55px)`,
              }}
            >
              <span className="absolute inset-0 rounded-full border border-dossier/45" />
              <span
                className="absolute rounded-full bg-dossier/90"
                style={{
                  width: n.r * 2,
                  height: n.r * 2,
                  left: `calc(50% - ${n.r}px)`,
                  top: `calc(50% - ${n.r}px)`,
                }}
              />
              <span className="absolute left-full top-1/2 ml-3 -translate-y-1/2 whitespace-nowrap font-mono text-[9px] tracking-[0.15em] text-gray-400">
                {n.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
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
      setTimeout(() => navigate('/dashboard'), 1050)
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
    <div className="login-bg flex min-h-screen flex-col lg:flex-row">
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

      {/* ── LEFT: case-file exhibit panel (desktop only) ── */}
      <div className="relative hidden flex-col justify-between overflow-hidden p-10 lg:flex lg:w-[55%] xl:p-14">
        {/* graph-paper dot grid */}
        <div className="login-graphic-grid pointer-events-none absolute inset-0" aria-hidden />
        {/* corner crop marks */}
        <span aria-hidden className="absolute left-5 top-5 h-4 w-4 border-l border-t border-white/25" />
        <span aria-hidden className="absolute right-5 top-5 h-4 w-4 border-r border-t border-white/25" />
        <span aria-hidden className="absolute bottom-5 left-5 h-4 w-4 border-b border-l border-white/25" />
        <span aria-hidden className="absolute bottom-5 right-5 h-4 w-4 border-b border-r border-white/25" />

        {/* top case-file strip */}
        <div className="relative font-mono text-[10px] uppercase tracking-[0.25em]">
          <p className="text-gray-400">Case file <span className="text-dossier">//</span> Apex Link</p>
          <p className="mt-1.5 text-gray-600">Exhibit A — Network Overview</p>
        </div>

        {/* constellation */}
        <div className="relative flex flex-1 items-center justify-center py-8">
          <CaseConstellation />
        </div>

        {/* bottom ledger line — real demo-dataset numbers */}
        <div className="relative font-mono text-[10px] tracking-[0.2em]">
          <p className="text-gray-500">
            15 CASES <span className="text-gray-700">·</span> 43 ENTITIES{' '}
            <span className="text-gray-700">·</span> 60 RELATIONSHIPS{' '}
            <span className="text-gray-700">·</span> 12 LEADS
          </p>
          <p className="mt-1.5 text-gray-600">Every score is a lead — not a verdict.</p>
        </div>
      </div>

      {/* ── RIGHT: offset form column — three-zone rhythm mirroring the exhibit panel ── */}
      <div className="flex w-full flex-1 flex-col border-white/10 bg-charcoal-light/70 px-6 py-6 sm:px-10 lg:w-[45%] lg:border-l xl:px-14 xl:py-8">
        {/* top zone — identity header pinned to the top edge */}
        <div className={`shrink-0 transition-opacity duration-300 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
          {/* identity header — left-aligned, not centered */}
          <div className="border-b border-white/10 pb-6">
            <div className="flex items-center gap-3">
              <img src="/logo-mark-white.svg" alt="APEX LINK logo" className="h-10 w-10" />
              <div>
                <h1 className="text-lg font-extrabold font-mono tracking-wider text-white">
                  APEX LINK
                </h1>
                <p className="mt-0.5 text-[10px] font-mono uppercase tracking-[0.18em] text-gray-500">
                  Investigation Intelligence Platform
                </p>
              </div>
            </div>
            <p className="mt-4 font-mono text-[9px] uppercase tracking-[0.3em] text-dossier/70">
              Authorized personnel only
            </p>
          </div>
        </div>

        {/* middle zone — card centered in the remaining height */}
        <div className="flex flex-1 items-center justify-center py-10">
        <div className={`w-full max-w-sm transition-all duration-300 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
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
        </div>
        </div>

        {/* bottom zone — honest footer strip pinned to the bottom edge */}
        <div
          className={`shrink-0 border-t border-white/10 pt-4 transition-opacity duration-300 ${
            mounted ? 'opacity-100' : 'opacity-0'
          }`}
        >
          <p className="font-mono text-[9px] uppercase tracking-[0.25em] text-gray-600">
            SIH26189 <span className="text-gray-700">·</span> v{pkg.version}{' '}
            <span className="text-gray-700">·</span> Synthetic data only — not for production use
          </p>
        </div>
      </div>
    </div>
  )
}
