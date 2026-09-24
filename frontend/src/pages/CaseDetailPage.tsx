import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { casesApi, evidenceApi, graphApi, analysisApi, leadsApi, timelineApi, correlationsApi, reportsApi } from '@/api'
import { Network, FileText, Clock, GitBranch, AlertTriangle, Play, Shield, ChevronRight, Map } from 'lucide-react'
import type { GraphResponse } from '@/types'
import { CytoscapeComponent } from '@/components/CytoscapeGraph'
import { MapView } from '@/components/MapView'

type Tab = 'overview' | 'evidence' | 'network' | 'leads' | 'timeline' | 'correlations' | 'reports'

const priorityBadge = (p: string) => {
  const classes: Record<string, string> = { CRITICAL: 'badge-critical', HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low' }
  return <span className={classes[p] || 'badge'}>{p}</span>
}

/** Graph/Map segmented toggle. Graph stays the default and only mounts MapView
 *  on demand — the two are independent rendering paths over the same data. */
function NetworkViewToggle({ graph }: { graph: GraphResponse }) {
  const [view, setView] = useState<'graph' | 'map'>('graph')
  const btn = (active: boolean) =>
    `flex items-center gap-1.5 px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-wider transition-colors ${
      active ? 'bg-dossier text-charcoal' : 'text-gray-400 hover:text-white hover:bg-charcoal-light'
    }`
  return (
    <div>
      <div className="flex items-center justify-between border-b border-mist-dark px-2 py-1.5">
        <span className="px-1 font-mono text-[9px] uppercase tracking-[0.2em] text-gray-500">
          Network Rendering
        </span>
        <div className="flex overflow-hidden rounded border border-mist-dark">
          <button onClick={() => setView('graph')} className={btn(view === 'graph')} aria-pressed={view === 'graph'}>
            <Network className="h-3 w-3" /> Graph View
          </button>
          <button onClick={() => setView('map')} className={btn(view === 'map')} aria-pressed={view === 'map'}>
            <Map className="h-3 w-3" /> Map View
          </button>
        </div>
      </div>
      {view === 'graph' ? <CytoscapeComponent graph={graph} /> : <MapView graph={graph} />}
    </div>
  )
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
    return <div className="card h-64 animate-pulse" />
  }

  if (!caseData) {
    return <div className="card"><p className="text-xs text-gray-500">Case not found.</p></div>
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
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-mist-dark pb-3">
        <div>
          <div className="flex items-center gap-1.5 text-[10px] text-gray-400 font-mono">
            <Link to="/cases" className="hover:text-crosscase transition-colors">Cases</Link>
            <ChevronRight className="h-3 w-3" />
            <span>{caseData.case_number}</span>
          </div>
          <h1 className="mt-1 text-lg font-bold text-ink font-mono tracking-wide">{caseData.title}</h1>
          <div className="mt-1.5 flex items-center gap-2">
            {priorityBadge(caseData.priority)}
            <span className="badge bg-cream-dark text-gray-600 border border-mist-dark">{caseData.status}</span>
            {caseData.location && <span className="text-xs text-gray-500 font-mono">{caseData.location}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/cases/${id}/investigation`}
            className="btn-primary text-xs"
          >
            <Network className="mr-1.5 h-3.5 w-3.5" /> Investigation
          </Link>
          <button
            onClick={() => analysisMutation.mutate()}
            disabled={analysisMutation.isPending}
            className="btn-primary text-xs"
          >
            {analysisMutation.isPending ? (
              <span className="flex items-center gap-1.5">
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-charcoal border-t-transparent" />
                Analyzing...
              </span>
            ) : (
              <><Play className="mr-1.5 h-3.5 w-3.5" /> Run Analysis</>
            )}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-mist-dark">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold font-mono border-b-2 -mb-px transition-colors ${
              tab === t.key
                ? 'border-dossier text-ink'
                : 'border-transparent text-gray-400 hover:text-gray-600'
            }`}
          >
            <t.icon className="h-3.5 w-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="min-h-[400px]">
        {tab === 'overview' && (
          <div className="space-y-4">
            <div className="card">
              <h2 className="section-header">Description</h2>
              <p className="text-sm text-gray-600">{caseData.description || 'No description.'}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="card">
                <p className="text-label text-gray-400">Category</p>
                <p className="mt-1 font-mono text-sm font-semibold text-ink">{caseData.category.replace(/_/g, ' ')}</p>
              </div>
              <div className="card">
                <p className="text-label text-gray-400">Incident Date</p>
                <p className="mt-1 font-mono text-sm font-semibold text-ink">
                  {caseData.incident_date ? new Date(caseData.incident_date).toLocaleDateString() : '—'}
                </p>
              </div>
            </div>
          </div>
        )}

        {tab === 'evidence' && (
          <div className="card">
            {evidence?.items && evidence.items.length > 0 ? (
              <div className="space-y-2">
                {evidence.items.map((ev: any) => (
                  <div key={ev.id} className="flex items-center justify-between rounded border border-mist-dark p-2.5 bg-cream/50">
                    <div>
                      <p className="font-mono text-xs font-semibold text-ink">{ev.evidence_number}</p>
                      <p className="text-[10px] text-gray-500">{ev.filename} — {ev.evidence_type}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="evidence-tag">{ev.sha256_hash.substring(0, 12)}…</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400 text-center py-8">No evidence uploaded yet.</p>
            )}
          </div>
        )}

        {tab === 'network' && (
          <div className="card min-h-[500px] p-0">
            {graph ? (
              <NetworkViewToggle graph={graph} />
            ) : (
              <p className="text-xs text-gray-400 text-center py-8">Loading graph...</p>
            )}
          </div>
        )}

        {tab === 'leads' && (
          <div className="space-y-2">
            {leads?.items && leads.items.length > 0 ? (
              leads.items.map((lead) => (
                <div key={lead.id} className="card">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        {priorityBadge(lead.priority)}
                        <span className={`badge ${
                          lead.status === 'NEW' ? 'bg-crosscase/10 text-crosscase border border-crosscase/20' :
                          lead.status === 'CONFIRMED' ? 'bg-field/10 text-field border border-field/20' :
                          lead.status === 'DISMISSED' ? 'bg-gray-100 text-gray-500 border border-mist-dark' :
                          'bg-dossier/10 text-dossier-dim border border-dossier/20'
                        }`}>{lead.status}</span>
                      </div>
                      <p className="mt-1.5 text-xs text-gray-600">{lead.explanation}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-2xl font-extrabold text-dossier leading-none">{lead.score}</p>
                      <span className="text-[9px] text-gray-400 font-mono">/100</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="card text-center py-8">
                <p className="text-xs text-gray-400">No leads generated yet. Run analysis to generate leads.</p>
              </div>
            )}
          </div>
        )}

        {tab === 'timeline' && (
          <div className="card">
            {timeline?.events && timeline.events.length > 0 ? (
              <div className="relative ml-3 border-l border-mist-dark pl-6 space-y-3">
                {timeline.events.map((event, i) => (
                  <div key={i} className="relative">
                    <div className="absolute -left-7 top-1 h-2.5 w-2.5 rounded-full border-2 border-dossier bg-cream" />
                    <p className="text-[10px] text-gray-400 font-mono">{new Date(event.timestamp).toLocaleString()}</p>
                    <p className="text-xs font-semibold text-ink">{event.event_type.replace(/_/g, ' ')}</p>
                    <p className="text-[10px] text-gray-500">{event.description}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400 text-center py-8">No timeline events yet.</p>
            )}
          </div>
        )}

        {tab === 'correlations' && (
          <div className="card">
            {correlations?.correlations && correlations.correlations.length > 0 ? (
              <div className="space-y-2">
                {correlations.correlations.map((c: any) => (
                  <div key={c.id} className="flex items-center justify-between rounded border border-mist-dark p-2.5">
                    <div>
                      <p className="text-xs font-semibold text-ink">Cross-case correlation</p>
                      <p className="text-[10px] text-gray-500">{c.explanation}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-lg font-bold text-dossier">{c.score}</p>
                      {priorityBadge(c.priority)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400 text-center py-8">
                No correlations found. Run analysis to discover cross-case links.
              </p>
            )}
          </div>
        )}

        {tab === 'reports' && (
          <div className="card space-y-3">
            <h2 className="text-sm font-bold font-mono text-ink">GENERATE REPORT</h2>
            <p className="text-xs text-gray-500">
              Generate a comprehensive analysis report for this case.
            </p>
            <button
              onClick={() => reportMutation.mutate()}
              disabled={reportMutation.isPending}
              className="btn-primary text-xs"
            >
              {reportMutation.isPending ? 'Generating...' : 'Generate Report (JSON)'}
            </button>
            {reportMutation.isSuccess && (
              <p className="text-xs text-field font-mono">Report downloaded successfully.</p>
            )}
            {reportMutation.isError && (
              <p className="text-xs text-alert font-mono">Failed to generate report. Please try again.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
