import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { casesApi, evidenceApi, graphApi, analysisApi, leadsApi, timelineApi, correlationsApi, reportsApi } from '@/api'
import { Network, FileText, Clock, GitBranch, AlertTriangle, Play, Shield, ChevronRight, ExternalLink } from 'lucide-react'
import { CytoscapeComponent } from '@/components/CytoscapeGraph'

type Tab = 'overview' | 'evidence' | 'network' | 'leads' | 'timeline' | 'correlations' | 'reports'

const priorityBadge = (p: string) => {
  const classes: Record<string, string> = { CRITICAL: 'badge-critical', HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low' }
  return <span className={classes[p] || 'badge'}>{p}</span>
}

export function CaseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('overview')

  const { data: caseData, isLoading } = useQuery({
    queryKey: ['case', id],
    queryFn: () => casesApi.get(id!).then((r) => r.data),
    enabled: !!id,
  })

  const { data: evidence } = useQuery({
    queryKey: ['evidence', id],
    queryFn: () => evidenceApi.list(id!).then((r) => r.data),
    enabled: !!id && tab === 'evidence',
  })

  const { data: graph } = useQuery({
    queryKey: ['graph', id],
    queryFn: () => graphApi.getForCase(id!).then((r) => r.data),
    enabled: !!id && tab === 'network',
  })

  const { data: leads } = useQuery({
    queryKey: ['leads', id],
    queryFn: () => leadsApi.list({ case_id: id! }).then((r) => r.data),
    enabled: !!id && tab === 'leads',
  })

  const { data: timeline } = useQuery({
    queryKey: ['timeline', id],
    queryFn: () => timelineApi.get(id!).then((r) => r.data),
    enabled: !!id && tab === 'timeline',
  })

  const { data: correlations } = useQuery({
    queryKey: ['correlations', id],
    queryFn: () => correlationsApi.get(id!).then((r) => r.data),
    enabled: !!id && tab === 'correlations',
  })

  const analysisMutation = useMutation({
    mutationFn: () => analysisApi.run(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graph', id] })
      queryClient.invalidateQueries({ queryKey: ['leads', id] })
      queryClient.invalidateQueries({ queryKey: ['timeline', id] })
    },
  })

  const reportMutation = useMutation({
    mutationFn: () => reportsApi.generate(id!),
    onSuccess: (response) => {
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report-${caseData?.case_number || 'unknown'}.json`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  if (isLoading) {
    return <div className="card animate-pulse h-64" />
  }

  if (!caseData) {
    return <div className="card"><p>Case not found.</p></div>
  }

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: 'overview', label: 'Overview', icon: FileText },
    { key: 'evidence', label: 'Evidence', icon: Shield },
    { key: 'network', label: 'Network', icon: Network },
    { key: 'leads', label: 'Leads', icon: AlertTriangle },
    { key: 'timeline', label: 'Timeline', icon: Clock },
    { key: 'correlations', label: 'Correlations', icon: GitBranch },
    { key: 'reports', label: 'Reports', icon: FileText },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Link to="/cases" className="hover:text-trace-600">Cases</Link>
            <ChevronRight className="h-4 w-4" />
            <span>{caseData.case_number}</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold">{caseData.title}</h1>
          <div className="mt-2 flex items-center gap-3">
            {priorityBadge(caseData.priority)}
            <span className="badge bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400">{caseData.status}</span>
            {caseData.location && <span className="text-sm text-gray-500">📍 {caseData.location}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/cases/${id}/investigation`}
            className="btn-primary inline-flex items-center"
          >
            <Network className="mr-2 h-4 w-4" /> Investigation Workspace
          </Link>
          <button
            onClick={() => analysisMutation.mutate()}
            disabled={analysisMutation.isPending}
            className="btn-primary"
          >
            {analysisMutation.isPending ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Analyzing...
              </span>
            ) : (
              <><Play className="mr-2 h-4 w-4" /> Run Analysis</>
            )}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-800">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-trace-600 text-trace-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="min-h-[400px]">
        {tab === 'overview' && (
          <div className="space-y-6">
            <div className="card">
              <h2 className="mb-2 text-lg font-semibold">Description</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">{caseData.description || 'No description.'}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="card">
                <h3 className="text-sm font-medium text-gray-500">Category</h3>
                <p className="mt-1 text-lg font-semibold">{caseData.category.replace(/_/g, ' ')}</p>
              </div>
              <div className="card">
                <h3 className="text-sm font-medium text-gray-500">Incident Date</h3>
                <p className="mt-1 text-lg font-semibold">
                  {caseData.incident_date ? new Date(caseData.incident_date).toLocaleDateString() : '—'}
                </p>
              </div>
            </div>
          </div>
        )}

        {tab === 'evidence' && (
          <div className="card">
            {evidence?.items && evidence.items.length > 0 ? (
              <div className="space-y-3">
                {evidence.items.map((ev: any) => (
                  <div key={ev.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                    <div>
                      <p className="font-mono text-sm font-medium">{ev.evidence_number}</p>
                      <p className="text-xs text-gray-500">{ev.filename} — {ev.evidence_type}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400 font-mono">{ev.sha256_hash.substring(0, 16)}...</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No evidence uploaded yet.</p>
            )}
          </div>
        )}

        {tab === 'network' && (
          <div className="card min-h-[500px]">
            {graph ? (
              <CytoscapeComponent graph={graph} />
            ) : (
              <p className="text-sm text-gray-500">Loading graph...</p>
            )}
          </div>
        )}

        {tab === 'leads' && (
          <div className="space-y-3">
            {leads?.items && leads.items.length > 0 ? (
              leads.items.map((lead) => (
                <div key={lead.id} className="card">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-medium">Lead</span>
                        {priorityBadge(lead.priority)}
                        <span className={`badge ${lead.status === 'NEW' ? 'bg-blue-100 text-blue-800' : lead.status === 'CONFIRMED' ? 'bg-green-100 text-green-800' : lead.status === 'DISMISSED' ? 'bg-gray-100 text-gray-600' : 'bg-yellow-100 text-yellow-800'}`}>
                          {lead.status}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{lead.explanation}</p>
                      <p className="mt-1 text-xs text-gray-500">Score: {lead.score}/100</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-trace-600">{lead.score}</p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="card">
                <p className="text-sm text-gray-500">
                  No leads generated yet. Run analysis to generate cross-case leads.
                </p>
              </div>
            )}
          </div>
        )}

        {tab === 'timeline' && (
          <div className="card">
            {timeline?.events && timeline.events.length > 0 ? (
              <div className="relative ml-3 border-l-2 border-gray-200 dark:border-gray-700 pl-6 space-y-4">
                {timeline.events.map((event, i) => (
                  <div key={i} className="relative">
                    <div className="absolute -left-8 top-1 h-3 w-3 rounded-full border-2 border-trace-600 bg-white dark:bg-gray-900" />
                    <p className="text-xs text-gray-400">{new Date(event.timestamp).toLocaleString()}</p>
                    <p className="text-sm font-medium">{event.event_type.replace(/_/g, ' ')}</p>
                    <p className="text-xs text-gray-500">{event.description}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No timeline events yet.</p>
            )}
          </div>
        )}

        {tab === 'correlations' && (
          <div className="card">
            {correlations?.correlations && correlations.correlations.length > 0 ? (
              <div className="space-y-3">
                {correlations.correlations.map((c: any) => (
                  <div key={c.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                    <div>
                      <p className="text-sm font-medium">Cross-case correlation</p>
                      <p className="text-xs text-gray-500">{c.explanation}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold">{c.score}</p>
                      {priorityBadge(c.priority)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                No correlations found. Run analysis or correlation to discover cross-case links.
              </p>
            )}
          </div>
        )}

        {tab === 'reports' && (
          <div className="card space-y-4">
            <h2 className="text-lg font-semibold">Generate Investigation Report</h2>
            <p className="text-sm text-gray-500">
              Generate a comprehensive analysis report for this case. The report will distinguish between
              observed facts and algorithmic inferences.
            </p>
            <button
              onClick={() => reportMutation.mutate()}
              disabled={reportMutation.isPending}
              className="btn-primary"
            >
              {reportMutation.isPending ? 'Generating...' : 'Generate Report (JSON)'}
            </button>
            {reportMutation.isSuccess && (
              <p className="text-sm text-green-600">Report downloaded successfully.</p>
            )}
            {reportMutation.isError && (
              <p className="text-sm text-red-600">Failed to generate report. Please try again.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
