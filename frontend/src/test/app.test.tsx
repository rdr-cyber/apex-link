import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, gcTime: 0 } },
})

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('TRACE-NET Frontend', () => {
  it('renders a basic component without crashing', () => {
    render(<div data-testid="app">TRACE-NET</div>, { wrapper: Wrapper })
    expect(screen.getByTestId('app')).toHaveTextContent('TRACE-NET')
  })

  it('can import ProtectedRoute', async () => {
    const mod = await import('@/components/ProtectedRoute')
    expect(mod.ProtectedRoute).toBeDefined()
  })

  it('can import MainLayout', async () => {
    const mod = await import('@/layouts/MainLayout')
    expect(mod.MainLayout).toBeDefined()
  })

  it('can import LoginPage', async () => {
    const mod = await import('@/pages/LoginPage')
    expect(mod.LoginPage).toBeDefined()
  })

  it('can import DashboardPage', async () => {
    const mod = await import('@/pages/DashboardPage')
    expect(mod.DashboardPage).toBeDefined()
  })

  it('can import InvestigationPage', async () => {
    const mod = await import('@/pages/InvestigationPage')
    expect(mod.default).toBeDefined()
  })

  it('can import LeadDetailPage', async () => {
    const mod = await import('@/pages/LeadDetailPage')
    expect(mod.default).toBeDefined()
  })

  it('can import CasesPage', async () => {
    const mod = await import('@/pages/CasesPage')
    expect(mod.CasesPage).toBeDefined()
  })

  it('can import EntitiesPage', async () => {
    const mod = await import('@/pages/EntitiesPage')
    expect(mod.EntitiesPage).toBeDefined()
  })
})
