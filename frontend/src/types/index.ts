export interface User {
  id: string
  username: string
  email: string
  full_name: string
  role: 'ADMIN' | 'INVESTIGATOR' | 'ANALYST'
  is_active: boolean
  email_verified: boolean
}

export interface Case {
  id: string
  case_number: string
  title: string
  description: string
  category: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  status: 'OPEN' | 'UNDER_REVIEW' | 'ANALYSIS' | 'CLOSED' | 'ARCHIVED'
  incident_date: string | null
  location: string | null
  created_by: string
  assigned_to: string | null
  created_at: string
  updated_at: string
}

export interface CaseListResponse {
  items: Case[]
  total: number
  page: number
  page_size: number
}

export interface EntityListResponse {
  items: Entity[]
  total: number
  page: number
  page_size: number
}

export interface Evidence {
  id: string
  case_id: string
  evidence_number: string
  evidence_type: string
  filename: string
  mime_type: string
  size_bytes: number
  sha256_hash: string
  description: string
  source: string
  collected_by: string | null
  collected_at: string | null
  created_at: string
}

export interface Entity {
  id: string
  entity_type: string
  canonical_value: string
  display_value: string
  normalized_value: string
  confidence: number
  created_at: string
  updated_at: string
}

export interface Relationship {
  id: string
  source_entity_id: string
  target_entity_id: string
  relationship_type: string
  confidence: number
  case_id: string
  source_evidence_id: string | null
  description: string
  created_at: string
  updated_at: string
}

export interface GraphNode {
  id: string
  label: string
  entity_type: string
  confidence: number
  degree: number
  betweenness: number
  closeness: number
  cases: string[]
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  relationship_type: string
  confidence: number
  label: string
}

export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: Record<string, number>
}

export interface Lead {
  id: string
  case_id: string
  related_case_id: string | null
  lead_type: string
  score: number
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  explanation: string
  status: 'NEW' | 'REVIEWING' | 'CONFIRMED' | 'DISMISSED'
  factors: string
  created_at: string
  reviewed_by: string | null
  reviewed_at: string | null
}

export interface LeadListResponse {
  items: Lead[]
  total: number
  page: number
  page_size: number
}

export interface DashboardStats {
  total_cases: number
  active_cases: number
  total_evidence: number
  total_entities: number
  total_relationships: number
  high_priority_leads: number
  cases_by_status: Record<string, number>
  cases_by_priority: Record<string, number>
  cases_by_category: Record<string, number>
  lead_priority_distribution: Record<string, number>
  entity_type_distribution: Record<string, number>
}

export interface SearchResult {
  type: string
  id: string
  label: string
  subtitle: string
  detail: string
}

export interface IntegrityResult {
  evidence_id: string
  stored_hash: string
  current_hash: string
  integrity_status: 'VERIFIED' | 'MISMATCH' | 'UNAVAILABLE'
}

export interface TimelineEvent {
  timestamp: string
  event_type: string
  entity_type?: string
  description: string
  evidence_id?: string
  entity_id?: string
  lead_id?: string
}

export interface KeyEntity {
  entity_id: string
  label: string
  entity_type: string
  score: number
  factors: {
    degree: number
    betweenness: number
    cross_case: number
  }
  cases: string[]
}

export interface SuspiciousPattern {
  pattern: string
  description: string
  entity_id?: string
  label?: string
  entity_type?: string
  [key: string]: unknown
}

export interface AuditLogEntry {
  id: string
  user_id: string
  action: string
  resource_type: string
  resource_id: string | null
  details: string
  ip_address: string | null
  timestamp: string | null
}
