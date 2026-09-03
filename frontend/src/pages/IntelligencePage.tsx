import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Route, ArrowRight, Search, GitBranch, Clock, AlertCircle,
  ChevronDown, ChevronRight, ExternalLink, X, Filter,
  Network, FileText, Zap, Target
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
      <div className="flex items-center gap-2 mb-3">
        <Route className="h-5 w-5 text-trace-600" />
        <h3 className="text-lg font-semibold">Network Path Finder</h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Source */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">From</label>
          <select value={sourceType} onChange={e => setSourceType(e.target.value)} className="input-field text-sm">
            <option value="CASE">Case</option>
            <option value="ENTITY">Entity</option>
          </select>
          {sourceType === 'CASE' ? (
            <select value={sourceId} onChange={e => setSourceId(e.target.value)} className="input-field text-sm">
              <option value="">Select case...</option>
              {cases?.map((c: any) => (
                <option key={c.id} value={c.id}>{c.case_number} — {c.title}</option>
              ))}
            </select>
          ) : (
            <input type="text" placeholder="Entity ID" value={sourceId} onChange={e => setSourceId(e.target.value)} className="input-field text-sm" />
          )}
        </div>

        {/* Target */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">To</label>
          <select value={targetType} onChange={e => setTargetType(e.target.value)} className="input-field text-sm">
            <option value="CASE">Case</option>
            <option value="ENTITY">Entity</option>
          </select>
          {targetType === 'CASE' ? (
            <select value={targetId} onChange={e => setTargetId(e.target.value)} className="input-field text-sm">
              <option value="">Select case...</option>
              {cases?.map((c: any) => (
                <option key={c.id} value={c.id}>{c.case_number} — {c.title}</option>
              ))}
            </select>
          ) : (
            <input type="text" placeholder="Entity ID" value={targetId} onChange={e => setTargetId(e.target.value)} className="input-field text-sm" />
          )}
        </div>
      </div>

      <button onClick={handleFind} disabled={!sourceId || !targetId || pathMutation.isPending} className="btn-primary">
        {pathMutation.isPending ? 'Searching...' : 'Find Connection'}
      </button>

      {pathMutation.isError && (
        <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
          <AlertCircle className="h-4 w-4 inline mr-1" />
          Error finding path. Please try again.
        </div>
      )}

      {result && (
        <div className="card">
          {result.path_found ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="px-3 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-sm font-medium">
                  Connection Found
                </div>
                <span className="text-sm text-gray-500">
                  {result.hop_count} hops · Path quality: {result.path_quality}/100
                </span>
              </div>

              {/* Visual path */}
              <div className="flex flex-wrap items-center gap-2 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                {result.path?.map((node: any, i: number) => (
                  <div key={i} className="flex items-center gap-2">
                    {i > 0 && <ArrowRight className="h-4 w-4 text-gray-400" />}
                    <div className="px-3 py-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 shadow-sm">
                      <p className="text-xs text-gray-500">{node.entity_type}</p>
                      <p className="text-sm font-medium">{node.display_value}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Edges */}
              <div className="space-y-1">
                <p className="text-xs font-medium text-gray-500 uppercase">Relationships</p>
                {result.edges?.map((edge: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <Zap className="h-3 w-3 text-amber-500" />
                    <span className="font-medium">{edge.relationship_type}</span>
                    <span className="text-gray-400">·</span>
                    <span className="text-gray-500">{edge.basis.replace(/_/g, ' ').toLowerCase()}</span>
                    <span className="text-gray-400">·</span>
                    <span className="text-gray-500">{(edge.confidence * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>

              {/* Supporting evidence */}
              {result.supporting_evidence?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase mb-1">Supporting Evidence</p>
                  <div className="flex flex-wrap gap-1">
                    {result.supporting_evidence.map((evId: string) => (
                      <span key={evId} className="px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 text-xs font-mono">
                        {evId.slice(0, 8)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Explanation */}
              <div className="p-3 rounded-lg bg-trace-50 dark:bg-trace-900/20 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">
                {result.explanation}
              </div>

              {/* Alternative paths */}
              {result.alternative_paths?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase mb-2">Alternative Paths</p>
                  {result.alternative_paths.map((alt: any, i: number) => (
                    <div key={i} className="p-2 rounded border border-gray-200 dark:border-gray-700 mb-2 text-sm">
                      <span className="font-medium">{alt.hop_count} hops</span> · Quality: {alt.path_quality}/100
                      <div className="flex flex-wrap items-center gap-1 mt-1">
                        {alt.path?.map((n: any, j: number) => (
                          <span key={j} className="text-xs text-gray-500">
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
              <Search className="h-10 w-10 text-gray-300 mx-auto mb-2" />
              <p className="text-gray-500">{result.message}</p>
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
      <div className="flex items-center gap-2 mb-3">
        <Target className="h-5 w-5 text-indigo-600" />
        <h3 className="text-lg font-semibold">Explain Connection</h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Case A</label>
          <select value={caseId} onChange={e => setCaseId(e.target.value)} className="input-field text-sm">
            <option value="">Select case...</option>
            {cases?.map((c: any) => (
              <option key={c.id} value={c.id}>{c.case_number} — {c.title}</option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Case B</label>
          <select value={relatedCaseId} onChange={e => setRelatedCaseId(e.target.value)} className="input-field text-sm">
            <option value="">Select case...</option>
            {cases?.filter((c: any) => c.id !== caseId).map((c: any) => (
              <option key={c.id} value={c.id}>{c.case_number} — {c.title}</option>
            ))}
          </select>
        </div>
      </div>

      <button onClick={handleExplain} disabled={!caseId || !relatedCaseId || caseId === relatedCaseId || explainMutation.isPending} className="btn-primary">
        {explainMutation.isPending ? 'Analyzing...' : 'Why Connected?'}
      </button>

      {result && (
        <div className="card space-y-4">
          {/* Score */}
          <div className="flex items-center gap-4">
            <div className={`text-4xl font-extrabold ${result.score >= 50 ? 'text-red-600' : result.score >= 25 ? 'text-amber-600' : 'text-green-600'}`}>
              {result.score}
            </div>
            <div>
              <p className="text-sm font-semibold">Correlation Score</p>
              <p className="text-xs text-gray-500">{result.case_a_number} ↔ {result.case_b_number}</p>
              <p className="text-xs text-gray-400">/ 100</p>
            </div>
          </div>

          {/* Factors */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-500 uppercase">Contributing Factors</p>
            {result.factors?.map((f: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-gray-800/50">
                <div>
                  <p className="text-sm font-medium">{f.description}</p>
                  <p className="text-xs text-gray-500">Observed: {f.observed_value}</p>
                </div>
                <span className="text-sm font-bold text-trace-600">+{f.weight}</span>
              </div>
            ))}
          </div>

          {/* Score Breakdown */}
          {result.raw_score !== undefined && result.raw_score !== result.normalized_score && (
            <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-sm">
              <p className="text-xs font-medium text-gray-500 uppercase mb-2">Score Breakdown</p>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Raw factor total:</span>
                <span className="font-mono font-medium">{result.raw_score}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Max possible:</span>
                <span className="font-mono font-medium">{result.max_possible}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Normalization:</span>
                <span className="font-mono font-medium">{result.raw_score} / {result.max_possible} × 100 = {result.normalized_score}</span>
              </div>
            </div>
          )}

          {/* How Calculated */}
          <details className="group">
            <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300 select-none">
              How is this score calculated?
            </summary>
            <div className="mt-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-xs text-gray-600 dark:text-gray-400 space-y-1">
              <p>The system combines configured analytical factors (shared identifiers, temporal proximity, network paths) and normalizes the result to a 0–100 correlation score.</p>
              <p>Factor weights: Phone +30, UPI +25, Email +20, Device +20, IP +15, Vehicle +15, Organization +10, Temporal +10, Network Path +8.</p>
              <p className="text-amber-600 dark:text-amber-400 font-medium">This score represents an analytical signal and does not establish criminal responsibility.</p>
            </div>
          </details>

          {/* Explanation */}
          <div className="p-3 rounded-lg bg-trace-50 dark:bg-trace-900/20 text-sm whitespace-pre-line">
            {result.explanation}
          </div>

          {/* Interpretation */}
          <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-sm text-amber-700 dark:text-amber-400">
            <Zap className="h-4 w-4 inline mr-1" />
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
  const caseColors: Record<string, string> = {}

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-3">
        <Clock className="h-5 w-5 text-emerald-600" />
        <h3 className="text-lg font-semibold">Compare Timeline</h3>
      </div>

      {/* Case selection */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Select cases ({selectedCases.length}/5)
        </label>
        <div className="flex flex-wrap gap-2">
          {cases?.map((c: any) => (
            <button
              key={c.id}
              onClick={() => toggleCase(c.id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                selectedCases.includes(c.id)
                  ? 'bg-trace-600 text-white border-trace-600'
                  : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-trace-400'
              }`}
            >
              {c.case_number}
            </button>
          ))}
        </div>
      </div>

      {/* Event type filter */}
      <select value={eventType} onChange={e => setEventType(e.target.value)} className="input-field text-sm w-auto">
        <option value="">All event types</option>
        <option value="EVIDENCE_COLLECTED">Evidence Collected</option>
        <option value="ENTITY_LINKED">Entity Linked</option>
        <option value="LEAD_CREATED">Lead Created</option>
      </select>

      <button onClick={handleCompare} disabled={selectedCases.length < 2 || timelineMutation.isPending} className="btn-primary">
        {timelineMutation.isPending ? 'Building Timeline...' : 'Compare Timeline'}
      </button>

      {result && (
        <div className="card space-y-4">
          {/* Observations */}
          {result.observations?.length > 0 && (
            <div className="p-3 rounded-lg bg-trace-50 dark:bg-trace-900/20 space-y-1">
              <p className="text-xs font-medium text-trace-600 uppercase">Timeline Observations</p>
              {result.observations.map((obs: string, i: number) => (
                <p key={i} className="text-sm text-gray-700 dark:text-gray-300">• {obs}</p>
              ))}
            </div>
          )}

          {/* Timeline events */}
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700" />

            {result.events?.map((ev: any, i: number) => {
              const caseIdx = result.cases?.findIndex((c: any) => c.id === ev.case_id) ?? 0
              const color = caseIdx === 0 ? 'bg-blue-500' : caseIdx === 1 ? 'bg-emerald-500' : 'bg-purple-500'

              return (
                <div key={i} className="relative pl-10 pb-4">
                  <div className={`absolute left-2.5 top-1 w-3 h-3 rounded-full ${color} ring-2 ring-white dark:ring-gray-900`} />

                  <div className="flex items-start gap-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${caseIdx === 0 ? 'bg-blue-100 text-blue-700' : caseIdx === 1 ? 'bg-emerald-100 text-emerald-700' : 'bg-purple-100 text-purple-700'}`}>
                          {ev.case_number}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(ev.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm font-medium mt-0.5">{ev.description}</p>
                      {ev.entity_type && ev.display_value && (
                        <p className="text-xs text-gray-500">{ev.entity_type}: {ev.display_value}</p>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Temporal proximity */}
          {result.temporal_proximity?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase mb-2">Temporal Proximity</p>
              {result.temporal_proximity.slice(0, 5).map((pair: any, i: number) => (
                <div key={i} className="text-sm p-2 rounded bg-amber-50 dark:bg-amber-900/20 mb-1">
                  <span className="font-medium">{pair.hours_apart}h</span> apart — {pair.event_a?.case_number} ↔ {pair.event_b?.case_number}
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
    { key: 'path', label: 'Find Connection', icon: Route },
    { key: 'explain', label: 'Explain Connection', icon: Target },
    { key: 'timeline', label: 'Compare Timeline', icon: Clock },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Intelligence Tools</h1>
        <p className="text-sm text-gray-500">Network path analysis, connection explanation, and cross-case timeline comparison.</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === tab.key
                ? 'bg-white dark:bg-gray-900 text-trace-700 dark:text-trace-300 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            <tab.icon className="h-4 w-4" />
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
