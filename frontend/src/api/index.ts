import apiClient from './client'

export const api = apiClient
import type {
  Case,
  CaseListResponse,
  Evidence,
  Entity,
  EntityListResponse,
  Relationship,
  GraphResponse,
  Lead,
  LeadListResponse,
  DashboardStats,
  SearchResult,
  IntegrityResult,
  TimelineEvent,
  KeyEntity,
  SuspiciousPattern,
  AuditLogEntry,
} from '@/types'

// Auth
export const authApi = {
  login: (username: string, password: string) =>
    apiClient.post('/auth/login', { username, password }),
  verifyChallenge: (challenge_id: string, answer: string) =>
    apiClient.post('/auth/login/verify-challenge', { challenge_id, answer }),
  refresh: (refresh_token: string) =>
    apiClient.post('/auth/refresh', { refresh_token }),
  me: () => apiClient.get('/auth/me'),
  requestVerification: (email: string) =>
    apiClient.post('/auth/verify-email/request', { email }),
  confirmVerification: (token: string) =>
    apiClient.post('/auth/verify-email/confirm', { token }),
  verificationStatus: (email: string) =>
    apiClient.get('/auth/verification-status', { params: { email } }),
}

// Cases
export const casesApi = {
  list: (params?: Record<string, string | number>) =>
    apiClient.get<CaseListResponse>('/cases', { params }),
  get: (id: string) => apiClient.get<Case>(`/cases/${id}`),
  create: (data: Partial<Case>) => apiClient.post<Case>('/cases', data),
  update: (id: string, data: Partial<Case>) => apiClient.put<Case>(`/cases/${id}`, data),
  delete: (id: string) => apiClient.delete(`/cases/${id}`),
}

// Evidence
export const evidenceApi = {
  list: (caseId: string, params?: Record<string, number>) =>
    apiClient.get(`/cases/${caseId}/evidence`, { params }),
  upload: (caseId: string, formData: FormData) =>
    apiClient.post(`/cases/${caseId}/evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  verifyIntegrity: (caseId: string, evidenceId: string) =>
    apiClient.get<IntegrityResult>(`/cases/${caseId}/evidence/${evidenceId}/integrity`),
}

// Entities
export const entitiesApi = {
  list: (params?: Record<string, string | number>) =>
    apiClient.get<EntityListResponse>('/entities', { params }),
  get: (id: string) => apiClient.get<Entity>(`/entities/${id}`),
}

// Relationships & Graph
export const graphApi = {
  getForCase: (caseId: string) =>
    apiClient.get<GraphResponse>(`/cases/${caseId}/relationships/graph`),
  getGlobal: () => apiClient.get<GraphResponse>('/cases/relationships/graph/global'),
}

// Analysis
export const analysisApi = {
  run: (caseId: string) => apiClient.post(`/cases/${caseId}/analysis/run`),
  extractText: (caseId: string, formData: FormData) =>
    apiClient.post(`/cases/${caseId}/analysis/extract-text`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getKeyEntities: (caseId: string) =>
    apiClient.get<KeyEntity[]>(`/cases/${caseId}/analysis/key-entities`),
  getPatterns: (caseId: string) =>
    apiClient.get<SuspiciousPattern[]>(`/cases/${caseId}/analysis/patterns`),
  ingestText: (caseId: string, formData: FormData) =>
    apiClient.post(`/cases/${caseId}/analysis/ingest/text`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

// Intelligence (Path Finder, Explain Connection, Cross-Case Timeline)
export const intelligenceApi = {
  findPath: (data: { source_type: string; source_id: string; target_type: string; target_id: string }) =>
    apiClient.post('/intelligence/path', data),
  casesForPath: () =>
    apiClient.get('/intelligence/cases-for-path'),
  explainConnection: (data: { case_id: string; related_case_id: string }) =>
    apiClient.post('/intelligence/explain-connection', data),
  crossCaseTimeline: (data: { case_ids: string[]; event_type?: string; entity_type?: string; date_from?: string; date_to?: string }) =>
    apiClient.post('/intelligence/cross-case-timeline', data),
}

// Correlations
export const correlationsApi = {
  run: (caseId: string) => apiClient.post(`/cases/${caseId}/correlations`),
  get: (caseId: string) => apiClient.get(`/cases/${caseId}/correlations`),
}

// Leads
export const leadsApi = {
  list: (params?: Record<string, string | number>) =>
    apiClient.get<LeadListResponse>('/leads', { params }),
  update: (leadId: string, data: { status: string }) =>
    apiClient.put<Lead>(`/leads/${leadId}`, data),
}

// Timeline
export const timelineApi = {
  get: (caseId: string, params?: Record<string, string>) =>
    apiClient.get<{ events: TimelineEvent[] }>(`/cases/${caseId}/timeline`, { params }),
}

// Reports
export const reportsApi = {
  generate: (caseId: string) => apiClient.post(`/reports/case/${caseId}`),
}

// Search
export const searchApi = {
  search: (q: string) => apiClient.get<{ results: SearchResult[]; total: number }>('/search', { params: { q } }),
}

// Dashboard
export const dashboardApi = {
  getStats: () => apiClient.get<DashboardStats>('/dashboard'),
}

// Audit
export const auditApi = {
  list: (params?: Record<string, string | number>) =>
    apiClient.get('/audit', { params }),
}
