import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Shield, CheckCircle, XCircle, AlertCircle, Loader2, Mail } from 'lucide-react'
import { api } from '@/api'

type VerifyStatus = 'loading' | 'success' | 'expired' | 'used' | 'invalid' | 'missing' | 'error'

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<VerifyStatus>(token ? 'loading' : 'missing')
  const [message, setMessage] = useState('')
  const [resendEmail, setResendEmail] = useState('')
  const [resendLoading, setResendLoading] = useState(false)
  const [resendMessage, setResendMessage] = useState('')

  useEffect(() => {
    if (!token) { setStatus('missing'); return }

    const verify = async () => {
      try {
        const res = await api.post('/auth/verify-email/confirm', { token })
        setStatus('success')
        setMessage(res.data.message)
      } catch (err: any) {
        const detail = err.response?.data?.detail || ''
        const errorCode = err.response?.headers?.['x-auth-error'] || ''
        if (errorCode === 'VERIFICATION_TOKEN_EXPIRED' || detail.toLowerCase().includes('expired')) {
          setStatus('expired'); setMessage('This verification link has expired.')
        } else if (errorCode === 'VERIFICATION_TOKEN_USED' || detail.toLowerCase().includes('used')) {
          setStatus('used'); setMessage('This verification link has already been used.')
        } else if (errorCode === 'INVALID_VERIFICATION_TOKEN' || detail.toLowerCase().includes('invalid')) {
          setStatus('invalid'); setMessage('This verification link is invalid.')
        } else {
          setStatus('error'); setMessage('An unexpected error occurred.')
        }
      }
    }
    verify()
  }, [token])

  const handleResend = async (e: React.FormEvent) => {
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

  const statusConfig: Record<string, { icon: React.ReactNode; color: string; title: string }> = {
    loading: { icon: <Loader2 className="h-10 w-10 animate-spin" />, color: 'text-dossier', title: 'Verifying your email...' },
    success: { icon: <CheckCircle className="h-10 w-10" />, color: 'text-field', title: 'Email Verified' },
    expired: { icon: <AlertCircle className="h-10 w-10" />, color: 'text-dossier-dim', title: 'Link Expired' },
    used: { icon: <CheckCircle className="h-10 w-10" />, color: 'text-crosscase', title: 'Already Verified' },
    invalid: { icon: <XCircle className="h-10 w-10" />, color: 'text-alert', title: 'Invalid Link' },
    missing: { icon: <XCircle className="h-10 w-10" />, color: 'text-alert', title: 'Missing Verification Link' },
    error: { icon: <XCircle className="h-10 w-10" />, color: 'text-alert', title: 'Verification Failed' },
  }

  const config = statusConfig[status]

  return (
    <div className="login-bg flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-dossier text-charcoal">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-extrabold text-white font-mono tracking-wider">TRACE-NET</h1>
          <p className="mt-0.5 text-xs text-gray-400 font-mono">Email Verification</p>
        </div>

        <div className="card-glass shadow-xl">
          <div className="flex flex-col items-center text-center p-4">
            <div className={`mb-3 ${config.color}`}>{config.icon}</div>
            <h2 className="text-sm font-bold text-ink mb-1">{config.title}</h2>
            {message && <p className="text-xs text-gray-500 mb-3">{message}</p>}

            {(status === 'success' || status === 'used') && (
              <Link to="/login" className="btn-primary mt-3 text-xs">Sign In</Link>
            )}

            {(status === 'expired' || status === 'invalid' || status === 'missing' || status === 'error') && (
              <div className="w-full mt-3">
                <div className="border-t border-mist-dark pt-3">
                  <p className="text-xs font-mono text-gray-400 mb-2 flex items-center gap-1">
                    <Mail className="h-3 w-3" /> Resend verification
                  </p>
                  <form onSubmit={handleResend} className="space-y-2">
                    <input
                      type="email"
                      value={resendEmail}
                      onChange={(e) => setResendEmail(e.target.value)}
                      placeholder="your@email.com"
                      className="input-field text-xs"
                      required
                    />
                    <button type="submit" disabled={resendLoading} className="btn-secondary w-full text-xs">
                      {resendLoading ? 'Sending...' : 'Send Verification Email'}
                    </button>
                  </form>
                  {resendMessage && <p className="mt-2 text-xs text-gray-500">{resendMessage}</p>}
                </div>
              </div>
            )}

            {status === 'loading' && (
              <p className="text-xs text-gray-400 mt-2">Please wait...</p>
            )}
          </div>

          <div className="border-t border-mist-dark p-3 text-center">
            <Link to="/login" className="text-xs text-crosscase hover:text-crosscase-dim font-mono">
              ← Back to Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
