import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { leadsApi } from '@/api'
import { AlertTriangle, CheckCircle, XCircle, Eye } from 'lucide-react'

const priorityBadge = (p: string) => {
  const classes: Record<string, string> = { CRITICAL: 'badge-critical', HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low' }
  return <span className={classes[p] || 'badge'}>{p}</span>
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
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-6 w-6 text-trace-600" />
        <h1 className="text-2xl font-bold">Investigation Leads</h1>
      </div>

      <div className="flex gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="input-field w-auto"
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
          className="input-field w-auto"
        >
          <option value="">All Priority</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card animate-pulse h-32" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {data?.items.map((lead) => (
            <div key={lead.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    {priorityBadge(lead.priority)}
                    <span className={`badge ${
                      lead.status === 'NEW' ? 'bg-blue-100 text-blue-800' :
                      lead.status === 'CONFIRMED' ? 'bg-green-100 text-green-800' :
                      lead.status === 'DISMISSED' ? 'bg-gray-100 text-gray-600' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>{lead.status}</span>
                    <span className="text-xs text-gray-400">{lead.lead_type.replace(/_/g, ' ')}</span>
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">{lead.explanation}</p>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>Score: <strong className="text-gray-700 dark:text-gray-300">{lead.score}/100</strong></span>
                    <span>Created: {new Date(lead.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 ml-4">
                  <p className="text-3xl font-bold text-trace-600">{lead.score}</p>
                  {lead.status === 'NEW' && (
                    <div className="flex gap-1">
                      <button
                        onClick={() => updateMutation.mutate({ leadId: lead.id, status: 'CONFIRMED' })}
                        className="rounded-lg bg-green-50 p-1.5 text-green-600 hover:bg-green-100"
                        title="Confirm lead"
                      >
                        <CheckCircle className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => updateMutation.mutate({ leadId: lead.id, status: 'DISMISSED' })}
                        className="rounded-lg bg-red-50 p-1.5 text-red-600 hover:bg-red-100"
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
              <p className="text-sm text-gray-500">No leads found. Run analysis on a case to generate leads.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
