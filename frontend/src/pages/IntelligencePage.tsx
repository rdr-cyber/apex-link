import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Route, ArrowRight, Search, Clock, AlertCircle,
  Network, Zap, Target
} from 'lucide-react'
import { intelligenceApi } from '@/api'

// ─── Path Finder Panel ───

function PathFinderPanel() {
  const [sourceType, setSourceType] = useState('CASE')
  const [targetType, setTargetType] = useState('CASE')
  const [sourceId, setSourceId] = useState('')
  const [targetId, setTargetId] = useState('')

  const { data: cases } = useQuery({
    queryKey: ['cases-for-path'],
    queryFn: () => intelligenceApi.casesForPath().then(r => r.data),
  })

  const pathMutation = useMutation({
    mutationFn: (data: any) => intelligenceApi.findPath(data).then(r => r.data),
  })

  const handleFind = () => {
    if (!sourceId || !targetId) return
    pathMutation.mutate({
      source_type: sourceType,
      source_id: sourceId,
      target_type: targetType,
      target_id: targetId,
    })
  }

  const result = pathMutation.data

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Route className="h-4 w-4 text-dossier" />
        <h3 className="text-sm font-bold font-mono text-ink tracking-wide">NETWORK PATH FINDER</h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-label text-gray-500">From</label>
          <select value={sourceType} onChange={e => setSourceType(e.target.value)} className="input-field text-xs">
            <option value="CASE">Case</option>
            <option value="ENTITY">Entity</option>
          </select>
          {sourceType === 'CASE' ? (
            <select value={sourceId} onChange={e => setSourceId(e.target.value)} className="input-field text-xs">
              <option value="">Select case...</option>
              {cases?.map((c: any) => (
                <option key={c.id} value={c.id}>{c.case_number} — {c.title}</option>
              ))}
            </select>
          ) : (
            <input type="text" placeholder="Entity ID" value={sourceId} onChange={e => setSourceId(e.target.value)} className="input-field text-xs font-mono" />
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-label text-gray-500">To</label>
          <select value={targetType} onChange={e => setTargetType(e.target.value)} className="input-field text-xs">
            <option value="CASE">Case</option>
            <option value="ENTITY">Entity</option>
          </select>
          {targetType === 'CASE' ? (
            <select value={targetId} onChange={e => setTargetId(e.target.value)} className="input-field text-xs">
              <option value="">Select case...</option>
              {cases?.map((c: any) => (
                <option key={c.id} value={c.id}>{c.case_number} — {c.title}</option>
              ))}
            </select>
          ) : (
            <input type="text" placeholder="Entity ID" value={targetId} onChange={e => setTargetId(e.target.value)} className="input-field text-xs font-mono" />
          )}
        </div>
      </div>

      <button onClick={handleFind} disabled={!sourceId || !targetId || pathMutation.isPending} className="btn-primary text-xs">
        {pathMutation.isPending ? 'Searching...' : 'Find Connection'}
      </button>

      {pathMutation.isError && (
        <div className="p-2 rounded bg-alert/10 text-alert text-xs border border-alert/20">
          <AlertCircle className="h-3.5 w-3.5 inline mr-1" />
          Error finding path. Please try again.
        </div>
      )}

      {result && (
        <div className="card bg-cream/50">
          {result.path_found ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="badge bg-field/10 text-field border border-field/20">Connection Found</span>
                <span className="text-xs text-gray-500 font-mono">
                  {result.hop_count} hops · quality {result.path_quality}/100
                </span>
              </div>

              {/* Visual path */}
              <div className="flex flex-wrap items-center gap-1.5 p-3 bg-white rounded border border-mist-dark">
                {result.path?.map((node: any, i: number) => (
                  <div key={i} className="flex items-center gap-1.5">
                    {i > 0 && <ArrowRight className="h-3.5 w-3.5 text-gray-300" />}
                    <div className="px-2.5 py-1.5 rounded bg-cream border border-mist-dark">
                      <p className="text-[9px] text-gray-400 font-mono uppercase">{node.entity_type}</p>
                      <p className="text-xs font-semibold font-mono text-ink">{node.display_value}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Edges */}
              <div className="space-y-1">
                <p className="section-header">Relationships</p>
                {result.edges?.map((edge: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <Zap className="h-3 w-3 text-dossier" />
                    <span className="font-semibold font-mono">{edge.relationship_type}</span>
                    <span className="text-gray-300">·</span>
                    <span className="text-gray-500">{edge.basis.replace(/_/g, ' ').toLowerCase()}</span>
                    <span className="text-gray-300">·</span>
                    <span className="font-mono text-dossier">{(edge.confidence * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>

              {/* Supporting evidence */}
              {result.supporting_evidence?.length > 0 && (
                <div>
                  <p className="section-header">Supporting Evidence</p>
                  <div className="flex flex-wrap gap-1">
                    {result.supporting_evidence.map((evId: string) => (
                      <span key={evId} className="evidence-tag">{evId.slice(0, 8)}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Explanation */}
              <div className="p-3 rounded bg-white border border-mist-dark text-xs text-gray-600 whitespace-pre-line font-mono leading-relaxed">
                {result.explanation}
              </div>

              {/* Alternative paths */}
              {result.alternative_paths?.length > 0 && (
                <div>
                  <p className="section-header">Alternative Paths</p>
                  {result.alternative_paths.map((alt: any, i: number) => (
                    <div key={i} className="p-2 rounded border border-mist-dark mb-1.5 text-xs bg-white">
                      <span className="font-mono font-semibold">{alt.hop_count} hops</span> · Quality: {alt.path_quality}/100
                      <div className="flex flex-wrap items-center gap-1 mt-1">
                        {alt.path?.map((n: any, j: number) => (
                          <span key={j} className="text-[10px] text-gray-500 font-mono">
                            {j > 0 && ' → '}{n.entity_type}: {n.display_value}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-6">
              <Search className="h-8 w-8 text-gray-300 mx-auto mb-2" />
              <p className="text-xs text-gray-400">{result.message}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Explain Connection Panel ───

function ExplainConnectionPanel() {
  const [caseId, setCaseId] = useState('')
  const [relatedCaseId, setRelatedCaseId] = useState('')

  const { data: cases } = useQuery({
    queryKey: ['cases-for-path'],
    queryFn: () => intelligenceApi.casesForPath().then(r => r.data),
  })

  const explainMutation = useMutation({
    mutationFn: (data: any) => intelligenceApi.explainConnection(data).then(r => r.data),
  })

  const handleExplain = () => {
    if (!caseId || !relatedCaseId || caseId === relatedCaseId) return
    explainMutation.mutate({ case_id: caseId, related_case_id: relatedCaseId })
  }

  const result = explainMutation.data

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Target className="h-4 w-4 text-crosscase" />
        <h3 className="text-sm font-bold font-mono text-ink tracking-wide">EXPLAIN CONNECTION</h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-label text-gray-500">Case A</label>
          <select value={caseId} onChange={e => setCaseId(e.target.value)} className="input-field text-xs">
            <option value="">Select case...</option>
            {cases?.map((c: any) => (
              <option key={c.id} value={c.id}>{c.case_number} — {c.title}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-label text-gray-500">Case B</label>
          <select value={relatedCaseId} onChange={e => setRelatedCaseId(e.target.value)} className="input-field text-xs">
            <option value="">Select case...</option>
            {cases?.filter((c: any) => c.id !== caseId).map((c: any) => (
              <option key={c.id} value={c.id}>{c.case_number} — {c.title}</option>
            ))}
          </select>
        </div>
      </div>

      <button onClick={handleExplain} disabled={!caseId || !relatedCaseId || caseId === relatedCaseId || explainMutation.isPending} className="btn-primary text-xs">
        {explainMutation.isPending ? 'Analyzing...' : 'Why Connected?'}
      </button>

      {result && (
        <div className="card bg-cream/50 space-y-3">
          {/* Score — bold monospace */}
          <div className="flex items-baseline gap-3">
            <div className={`font-mono text-4xl font-extrabold leading-none ${
              result.score >= 50 ? 'text-alert' : result.score >= 25 ? 'text-dossier' : 'text-field'
            }`}>
              {result.score}
            </div>
            <div>
              <p className="text-xs font-semibold text-ink">Correlation Score</p>
              <p className="text-[10px] text-gray-400 font-mono">{result.case_a_number} ↔ {result.case_b_number}</p>
            </div>
          </div>

          {/* Factors */}
          <div className="space-y-1.5">
            <p className="section-header">Contributing Factors</p>
            {result.factors?.map((f: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-white border border-mist-dark">
                <div>
                  <p className="text-xs font-semibold text-ink">{f.description}</p>
                  <p className="text-[10px] text-gray-400 font-mono">Observed: {f.observed_value}</p>
                </div>
                <span className="font-mono text-xs font-bold text-dossier">+{f.weight}</span>
              </div>
            ))}
          </div>

          {/* Score Breakdown */}
          {result.raw_score !== undefined && result.raw_score !== result.normalized_score && (
            <div className="p-2.5 rounded bg-white border border-mist-dark text-xs font-mono space-y-0.5">
              <p className="section-header">Score Breakdown</p>
              <div className="flex justify-between">
                <span className="text-gray-500">Raw factor total:</span>
                <span className="font-bold">{result.raw_score}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Max possible:</span>
                <span className="font-bold">{result.max_possible}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Normalized:</span>
                <span className="font-bold">{result.raw_score}/{result.max_possible} × 100 = {result.normalized_score}</span>
              </div>
            </div>
          )}

          {/* How Calculated */}
          <details className="group">
            <summary className="text-[10px] text-gray-400 cursor-pointer hover:text-gray-600 select-none font-mono">
              How is this score calculated?
            </summary>
            <div className="mt-2 p-2.5 rounded bg-white border border-mist-dark text-[10px] text-gray-500 font-mono space-y-1">
              <p>Combines configured analytical factors (shared identifiers, temporal proximity, network paths) normalized to 0–100.</p>
              <p>Factor weights: Phone +30, UPI +25, Email +20, Device +20, IP +15, Vehicle +15, Organization +10, Temporal +10, Network Path +8.</p>
              <p className="text-dossier-dim font-semibold">This score represents an analytical signal. It does not establish criminal responsibility.</p>
            </div>
          </details>

          {/* Explanation */}
          <div className="p-3 rounded bg-white border border-mist-dark text-xs text-gray-600 whitespace-pre-line font-mono leading-relaxed">
            {result.explanation}
          </div>

          {/* Interpretation */}
          <div className="p-2.5 rounded bg-dossier/5 border border-dossier/20 text-xs text-dossier-dim">
            <Zap className="h-3.5 w-3.5 inline mr-1" />
            {result.interpretation}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Cross-Case Timeline Panel ───

function CrossCaseTimelinePanel() {
  const [selectedCases, setSelectedCases] = useState<string[]>([])
  const [eventType, setEventType] = useState('')

  const { data: cases } = useQuery({
    queryKey: ['cases-for-path'],
    queryFn: () => intelligenceApi.casesForPath().then(r => r.data),
  })

  const timelineMutation = useMutation({
    mutationFn: (data: any) => intelligenceApi.crossCaseTimeline(data).then(r => r.data),
  })

  const handleCompare = () => {
    if (selectedCases.length < 2) return
    timelineMutation.mutate({
      case_ids: selectedCases,
      event_type: eventType || undefined,
    })
  }

  const toggleCase = (cid: string) => {
    setSelectedCases(prev =>
      prev.includes(cid) ? prev.filter(c => c !== cid) : [...prev, cid]
    )
  }

  const result = timelineMutation.data

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Clock className="h-4 w-4 text-field" />
        <h3 className="text-sm font-bold font-mono text-ink tracking-wide">COMPARE TIMELINE</h3>
      </div>

      {/* Case selection */}
      <div className="space-y-1.5">
        <label className="text-label text-gray-500">
          Select cases ({selectedCases.length}/5)
        </label>
        <div className="flex flex-wrap gap-1.5">
          {cases?.map((c: any) => (
            <button
              key={c.id}
              onClick={() => toggleCase(c.id)}
              className={`px-2.5 py-1 rounded text-xs font-mono font-semibold border transition-colors ${
                selectedCases.includes(c.id)
                  ? 'bg-charcoal text-dossier border-charcoal'
                  : 'bg-white text-gray-600 border-mist-dark hover:border-dossier/40'
              }`}
            >
              {c.case_number}
            </button>
          ))}
        </div>
      </div>

      {/* Event type filter */}
      <select value={eventType} onChange={e => setEventType(e.target.value)} className="input-field text-xs w-auto">
        <option value="">All event types</option>
        <option value="EVIDENCE_COLLECTED">Evidence Collected</option>
        <option value="ENTITY_LINKED">Entity Linked</option>
        <option value="LEAD_CREATED">Lead Created</option>
      </select>

      <button onClick={handleCompare} disabled={selectedCases.length < 2 || timelineMutation.isPending} className="btn-primary text-xs">
        {timelineMutation.isPending ? 'Building Timeline...' : 'Compare Timeline'}
      </button>

      {result && (
        <div className="card bg-cream/50 space-y-3">
          {/* Observations */}
          {result.observations?.length > 0 && (
            <div className="p-2.5 rounded bg-dossier/5 border border-dossier/15">
              <p className="section-header">Timeline Observations</p>
              {result.observations.map((obs: string, i: number) => (
                <p key={i} className="text-xs text-gray-600 font-mono">• {obs}</p>
              ))}
            </div>
          )}

          {/* Timeline events */}
          <div className="relative">
            <div className="absolute left-3.5 top-0 bottom-0 w-px bg-mist-dark" />

            {result.events?.map((ev: any, i: number) => {
              const caseIdx = result.cases?.findIndex((c: any) => c.id === ev.case_id) ?? 0
              const dotColor = caseIdx === 0 ? 'bg-crosscase' : caseIdx === 1 ? 'bg-field' : 'bg-dossier'
              const tagColor = caseIdx === 0 ? 'bg-crosscase/10 text-crosscase' : caseIdx === 1 ? 'bg-field/10 text-field' : 'bg-dossier/10 text-dossier-dim'

              return (
                <div key={i} className="relative pl-9 pb-3">
                  <div className={`absolute left-2.5 top-1 w-2.5 h-2.5 rounded-full ${dotColor} ring-2 ring-cream`} />

                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className={`px-1.5 py-0.5 rounded-sm text-[9px] font-mono font-bold ${tagColor}`}>
                        {ev.case_number}
                      </span>
                      <span className="text-[10px] text-gray-400 font-mono">
                        {new Date(ev.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-ink mt-0.5">{ev.description}</p>
                    {ev.entity_type && ev.display_value && (
                      <p className="text-[10px] text-gray-400 font-mono">{ev.entity_type}: {ev.display_value}</p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Temporal proximity */}
          {result.temporal_proximity?.length > 0 && (
            <div>
              <p className="section-header">Temporal Proximity</p>
              {result.temporal_proximity.slice(0, 5).map((pair: any, i: number) => (
                <div key={i} className="text-xs p-2 rounded bg-dossier/5 border border-dossier/15 mb-1 font-mono">
                  <span className="font-bold text-dossier">{pair.hours_apart}h</span> apart — {pair.event_a?.case_number} ↔ {pair.event_b?.case_number}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Main Intelligence Page ───

export default function IntelligencePage() {
  const [activeTab, setActiveTab] = useState<'path' | 'explain' | 'timeline'>('path')

  const tabs = [
    { key: 'path', label: 'Path Finder', icon: Route },
    { key: 'explain', label: 'Explain', icon: Target },
    { key: 'timeline', label: 'Timeline', icon: Clock },
  ]

  return (
    <div className="space-y-5">
      <div className="border-b border-mist-dark pb-3">
        <h1 className="text-lg font-bold text-ink font-mono tracking-wide">INTELLIGENCE</h1>
        <p className="text-xs text-gray-400 mt-0.5">Network path analysis, connection explanation, cross-case timeline.</p>
      </div>

      {/* Tab bar — minimal, no background */}
      <div className="flex gap-0 border-b border-mist-dark">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold font-mono transition-colors border-b-2 -mb-px ${
              activeTab === tab.key
                ? 'border-dossier text-ink'
                : 'border-transparent text-gray-400 hover:text-gray-600'
            }`}
          >
            <tab.icon className="h-3.5 w-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active panel */}
      <div className="card">
        {activeTab === 'path' && <PathFinderPanel />}
        {activeTab === 'explain' && <ExplainConnectionPanel />}
        {activeTab === 'timeline' && <CrossCaseTimelinePanel />}
      </div>
    </div>
  )
}
