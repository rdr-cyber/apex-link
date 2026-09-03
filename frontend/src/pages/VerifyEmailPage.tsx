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
    if (!token) {
      setStatus('missing')
      return
    }

    const verify = async () => {
      try {
        const res = await api.post('/auth/verify-email/confirm', { token })
        setStatus('success')
        setMessage(res.data.message)
      } catch (err: any) {
        const detail = err.response?.data?.detail || ''
        const errorCode = err.response?.headers?.['x-auth-error'] || ''

        if (errorCode === 'VERIFICATION_TOKEN_EXPIRED' || detail.toLowerCase().includes('expired')) {
          setStatus('expired')
          setMessage('This verification link has expired.')
        } else if (errorCode === 'VERIFICATION_TOKEN_USED' || detail.toLowerCase().includes('used')) {
          setStatus('used')
          setMessage('This verification link has already been used.')
        } else if (errorCode === 'INVALID_VERIFICATION_TOKEN' || detail.toLowerCase().includes('invalid')) {
          setStatus('invalid')
          setMessage('This verification link is invalid.')
        } else {
          setStatus('error')
          setMessage('An unexpected error occurred. Please try again.')
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
    loading: {
      icon: <Loader2 className="h-12 w-12 animate-spin" />,
      color: 'text-trace-600',
      title: 'Verifying your email...',
    },
    success: {
      icon: <CheckCircle className="h-12 w-12" />,
      color: 'text-green-600',
      title: 'Email Verified!',
    },
    expired: {
      icon: <AlertCircle className="h-12 w-12" />,
      color: 'text-amber-600',
      title: 'Link Expired',
    },
    used: {
      icon: <CheckCircle className="h-12 w-12" />,
      color: 'text-blue-600',
      title: 'Already Verified',
    },
    invalid: {
      icon: <XCircle className="h-12 w-12" />,
      color: 'text-red-600',
      title: 'Invalid Link',
    },
    missing: {
      icon: <XCircle className="h-12 w-12" />,
      color: 'text-red-600',
      title: 'Missing Verification Link',
    },
    error: {
      icon: <XCircle className="h-12 w-12" />,
      color: 'text-red-600',
      title: 'Verification Failed',
    },
  }

  const config = statusConfig[status]

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-trace-600">
            <Shield className="h-10 w-10 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">TRACE-NET</h1>
          <p className="mt-1 text-sm text-gray-500">Email Verification</p>
        </div>

        {/* Status Panel */}
        <div className="card">
          <div className="flex flex-col items-center text-center p-6">
            <div className={`mb-4 ${config.color}`}>{config.icon}</div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">{config.title}</h2>
            {message && <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">{message}</p>}

            {(status === 'success' || status === 'used') && (
              <Link to="/login" className="btn-primary mt-4">
                Sign In
              </Link>
            )}

            {(status === 'expired' || status === 'invalid' || status === 'missing' || status === 'error') && (
              <div className="w-full mt-4">
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <Mail className="h-4 w-4" /> Resend verification email
                  </p>
                  <form onSubmit={handleResend} className="space-y-3">
                    <input
                      type="email"
                      value={resendEmail}
                      onChange={(e) => setResendEmail(e.target.value)}
                      placeholder="your@email.com"
                      className="input-field"
                      required
                    />
                    <button
                      type="submit"
                      disabled={resendLoading}
                      className="btn-primary w-full"
                    >
                      {resendLoading ? 'Sending...' : 'Resend Verification Email'}
                    </button>
                  </form>
                  {resendMessage && (
                    <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">{resendMessage}</p>
                  )}
                </div>
              </div>
            )}

            {status === 'loading' && (
              <p className="text-sm text-gray-500 mt-2">Please wait while we verify your email address...</p>
            )}
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 p-4 text-center">
            <Link to="/login" className="text-sm text-trace-600 hover:text-trace-700 font-medium">
              ← Back to Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
