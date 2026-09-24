import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { LoginPage } from '@/pages/LoginPage'
import { VerifyEmailPage } from '@/pages/VerifyEmailPage'
import { AuthProvider } from '@/features/auth/AuthProvider'

const mockApiPost = vi.fn()
const mockAuthApiLogin = vi.fn()
const mockAuthApiMe = vi.fn()

vi.mock('@/api', () => ({
  api: {
    post: (...args: any[]) => mockApiPost(...args),
    get: vi.fn(),
  },
  authApi: {
    login: (...args: any[]) => mockAuthApiLogin(...args),
    me: (...args: any[]) => mockAuthApiMe(...args),
  },
}))

function renderWithProviders(ui: React.ReactElement, route = '/login') {
  mockAuthApiMe.mockRejectedValue(new Error('No token'))
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AuthProvider>{ui}</AuthProvider>
    </MemoryRouter>
  )
}

async function fillAndSubmit(
  user: ReturnType<typeof userEvent.setup>,
  username: string,
  password: string,
) {
  await user.type(screen.getByRole('textbox'), username)
  // Password fields have role "textbox" in jsdom sometimes, but safer to use placeholder
  const pwInput = document.querySelector('input[type="password"]') as HTMLInputElement
  await user.type(pwInput, password)
  await user.click(screen.getByRole('button', { name: /sign in/i }))
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    mockAuthApiMe.mockRejectedValue(new Error('No token'))
  })

  it('renders login form elements', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByText('APEX LINK')).toBeDefined()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeDefined()
    expect(screen.getByText(/demo accounts/i)).toBeDefined()
  })

  it('renders APEX LINK branding', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByText('APEX LINK')).toBeDefined()
    expect(screen.getByText(/investigation intelligence platform/i)).toBeDefined()
  })

  it('shows loading state during login', async () => {
    mockAuthApiLogin.mockImplementation(() => new Promise(() => {}))

    renderWithProviders(<LoginPage />)
    const user = userEvent.setup()
    await fillAndSubmit(user, 'admin', 'admin123')

    await waitFor(() => {
      expect(screen.getByText(/authenticating/i)).toBeDefined()
    })
  })

  it('displays error message on failed login', async () => {
    mockAuthApiLogin.mockRejectedValue({
      response: { status: 401, data: { detail: 'Invalid credentials.' }, headers: {} },
    })

    renderWithProviders(<LoginPage />)
    const user = userEvent.setup()
    await fillAndSubmit(user, 'admin', 'wrongpass')

    await waitFor(() => {
      expect(screen.getByText(/incorrect username or password/i)).toBeDefined()
    })
  })

  it('shows email not verified message with resend form', async () => {
    mockAuthApiLogin.mockRejectedValue({
      response: {
        status: 403,
        data: { detail: 'Please verify your email before signing in.' },
        headers: { 'x-auth-error': 'EMAIL_NOT_VERIFIED' },
      },
    })

    renderWithProviders(<LoginPage />)
    const user = userEvent.setup()
    await fillAndSubmit(user, 'unverified', 'pass123')

    await waitFor(() => {
      expect(screen.getByText(/email has not been verified/i)).toBeDefined()
      expect(screen.getByText(/send verification email/i)).toBeDefined()
    })
  })

  it('shows rate limit message', async () => {
    mockAuthApiLogin.mockRejectedValue({
      response: { status: 429, data: { detail: 'Too many requests.' }, headers: {} },
    })

    renderWithProviders(<LoginPage />)
    const user = userEvent.setup()
    await fillAndSubmit(user, 'admin', 'pass')

    await waitFor(() => {
      expect(screen.getByText(/too many login attempts/i)).toBeDefined()
    })
  })

  it('shows server error message on network failure', async () => {
    mockAuthApiLogin.mockRejectedValue(new Error('Network Error'))

    renderWithProviders(<LoginPage />)
    const user = userEvent.setup()
    await fillAndSubmit(user, 'admin', 'pass')

    await waitFor(() => {
      expect(screen.getByText(/unable to connect to the server/i)).toBeDefined()
    })
  })
})

describe('VerifyEmailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAuthApiMe.mockRejectedValue(new Error('No token'))
  })

  it('shows missing token message when no token in URL', () => {
    renderWithProviders(<VerifyEmailPage />, '/verify-email')
    expect(screen.getByText(/missing verification link/i)).toBeDefined()
  })

  it('shows loading state when verifying', async () => {
    mockApiPost.mockImplementation(() => new Promise(() => {}))
    renderWithProviders(<VerifyEmailPage />, '/verify-email?token=test-token')
    await waitFor(() => {
      expect(screen.getByText(/verifying your email/i)).toBeDefined()
    })
  })

  it('shows success on valid token', async () => {
    mockApiPost.mockResolvedValue({ data: { message: 'Email verified successfully.' } })
    renderWithProviders(<VerifyEmailPage />, '/verify-email?token=valid-token')
    await waitFor(() => {
      expect(screen.getByText('Email Verified')).toBeDefined()
    })
  })

  it('shows expired message for expired token', async () => {
    mockApiPost.mockRejectedValue({
      response: {
        status: 400,
        data: { detail: 'This verification link has expired.' },
        headers: { 'x-auth-error': 'VERIFICATION_TOKEN_EXPIRED' },
      },
    })
    renderWithProviders(<VerifyEmailPage />, '/verify-email?token=expired-token')
    await waitFor(() => {
      expect(screen.getByText('Link Expired')).toBeDefined()
    })
  })

  it('shows used message for already-used token', async () => {
    mockApiPost.mockRejectedValue({
      response: {
        status: 400,
        data: { detail: 'This verification link has already been used.' },
        headers: { 'x-auth-error': 'VERIFICATION_TOKEN_USED' },
      },
    })
    renderWithProviders(<VerifyEmailPage />, '/verify-email?token=used-token')
    await waitFor(() => {
      expect(screen.getByText('Already Verified')).toBeDefined()
    })
  })

  it('shows resend form on invalid token', async () => {
    mockApiPost.mockRejectedValue({
      response: {
        status: 400,
        data: { detail: 'Invalid verification token.' },
        headers: {},
      },
    })
    renderWithProviders(<VerifyEmailPage />, '/verify-email?token=bad-token')
    await waitFor(() => {
      expect(screen.getByText('Invalid Link')).toBeDefined()
    })
  })

  it('renders APEX LINK branding', () => {
    renderWithProviders(<VerifyEmailPage />, '/verify-email')
    expect(screen.getByText('APEX LINK')).toBeDefined()
    expect(screen.getByText(/email verification/i)).toBeDefined()
  })

  it('has back to sign in link', () => {
    renderWithProviders(<VerifyEmailPage />, '/verify-email')
    expect(screen.getByText(/back to sign in/i)).toBeDefined()
  })
})
