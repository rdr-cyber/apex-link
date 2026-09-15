import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { leadsApi } from '@/api'
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

const priorityBadge = (p: string) => {
  const classes: Record<string, string> = { CRITICAL: 'badge-critical', HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low' }
  return <span className={classes[p] || 'badge'}>{p}</span>
}

const statusStyle = (s: string) => {
  const map: Record<string, string> = {
    NEW: 'bg-crosscase/10 text-crosscase border border-crosscase/20',
    REVIEWING: 'bg-dossier/10 text-dossier-dim border border-dossier/20',
    CONFIRMED: 'bg-field/10 text-field border border-field/20',
    DISMISSED: 'bg-gray-100 text-gray-500 border border-mist-dark',
  }
  return `badge ${map[s] || 'badge'}`
}

export function LeadsPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['leads', page, statusFilter, priorityFilter],
    queryFn: () =>
      leadsApi
        .list({
          page,
          page_size: 20,
          ...(statusFilter && { status: statusFilter }),
          ...(priorityFilter && { priority: priorityFilter }),
        })
        .then((r) => r.data),
  })

  const updateMutation = useMutation({
    mutationFn: ({ leadId, status }: { leadId: string; status: string }) =>
      leadsApi.update(leadId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  return (
    <div className="space-y-5">
      <div className="flex items-baseline justify-between border-b border-mist-dark pb-3">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-bold text-ink font-mono tracking-wide">LEADS</h1>
          <AlertTriangle className="h-4 w-4 text-dossier" />
        </div>
      </div>

      <div className="flex gap-2">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="input-field w-auto text-xs"
        >
          <option value="">All Status</option>
          <option value="NEW">New</option>
          <option value="REVIEWING">Reviewing</option>
          <option value="CONFIRMED">Confirmed</option>
          <option value="DISMISSED">Dismissed</option>
        </select>
        <select
          value={priorityFilter}
          onChange={(e) => { setPriorityFilter(e.target.value); setPage(1) }}
          className="input-field w-auto text-xs"
        >
          <option value="">All Priority</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card h-24 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {data?.items.map((lead) => (
            <div key={lead.id} className="card">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    {priorityBadge(lead.priority)}
                    <span className={statusStyle(lead.status)}>{lead.status}</span>
                    <span className="evidence-tag">{lead.lead_type.replace(/_/g, ' ')}</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-1.5 leading-relaxed">{lead.explanation}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-400 font-mono">
                    <span>Created {new Date(lead.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 shrink-0">
                  <div className="font-mono text-3xl font-extrabold text-dossier leading-none">{lead.score}</div>
                  <span className="text-[9px] text-gray-400 font-mono">/100</span>
                  {lead.status === 'NEW' && (
                    <div className="flex gap-1 mt-1">
                      <button
                        onClick={() => updateMutation.mutate({ leadId: lead.id, status: 'CONFIRMED' })}
                        className="rounded p-1.5 text-field hover:bg-field/10 transition-colors"
                        title="Confirm lead"
                      >
                        <CheckCircle className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => updateMutation.mutate({ leadId: lead.id, status: 'DISMISSED' })}
                        className="rounded p-1.5 text-alert hover:bg-alert/10 transition-colors"
                        title="Dismiss lead"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {data?.items.length === 0 && (
            <div className="card text-center py-12">
              <p className="text-xs text-gray-400 font-mono">No leads found. Run analysis on a case to generate leads.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
