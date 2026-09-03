import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/features/auth/AuthProvider'
import { LoginPage } from '@/pages/LoginPage'
import { VerifyEmailPage } from '@/pages/VerifyEmailPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { CasesPage } from '@/pages/CasesPage'
import CreateCasePage from '@/pages/CreateCasePage'
import { CaseDetailPage } from '@/pages/CaseDetailPage'
import InvestigationPage from '@/pages/InvestigationPage'
import { EntitiesPage } from '@/pages/EntitiesPage'
import { LeadsPage } from '@/pages/LeadsPage'
import LeadDetailPage from '@/pages/LeadDetailPage'
import { SearchPage } from '@/pages/SearchPage'
import IntelligencePage from '@/pages/IntelligencePage'
import { AuditPage } from '@/pages/AuditPage'
import { MainLayout } from '@/layouts/MainLayout'
import { ProtectedRoute } from '@/components/ProtectedRoute'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="cases" element={<CasesPage />} />
            <Route path="cases/new" element={<CreateCasePage />} />
            <Route path="cases/:id" element={<CaseDetailPage />} />
            <Route path="cases/:id/investigation" element={<InvestigationPage />} />
            <Route path="entities" element={<EntitiesPage />} />
            <Route path="leads" element={<LeadsPage />} />
            <Route path="leads/:id" element={<LeadDetailPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="intelligence" element={<IntelligencePage />} />
            <Route path="audit" element={<AuditPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
