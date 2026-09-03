import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Network, Eye, FileText, Users, AlertTriangle, Clock,
  ChevronDown, ChevronRight, ExternalLink, X, Search,
  Filter, Activity, Shield, Link2, Target, Zap,
  CheckCircle, XCircle, RotateCcw, Download
} from 'lucide-react';
import { api } from '../api';
import { CytoscapeComponent } from '../components/CytoscapeGraph';

// Entity type colors
const ENTITY_COLORS: Record<string, string> = {
  PERSON: '#6366f1', PHONE: '#22c55e', EMAIL: '#3b82f6',
  IP_ADDRESS: '#f59e0b', UPI_ID: '#ef4444', BANK_ACCOUNT: '#8b5cf6',
  VEHICLE: '#06b6d4', DEVICE: '#f97316', LOCATION: '#ec4899',
  ORGANIZATION: '#14b8a6', SOCIAL_ACCOUNT: '#a855f7', URL: '#64748b',
  CASE_REFERENCE: '#6b7280',
};

const REL_COLORS: Record<string, string> = {
  SHARED_IDENTIFIER: '#22c55e', STRUCTURED_RECORD: '#3b82f6',
  TEXTUAL_CO_OCCURRENCE: '#94a3b8', CROSS_CASE_LINK: '#ef4444',
  TEMPORAL_ASSOCIATION: '#f59e0b', MANUAL: '#8b5cf6',
};

type EntityType = 'PERSON' | 'PHONE' | 'EMAIL' | 'IP_ADDRESS' | 'UPI_ID' | 'BANK_ACCOUNT' | 'VEHICLE' | 'DEVICE' | 'LOCATION' | 'ORGANIZATION' | 'SOCIAL_ACCOUNT' | 'URL' | 'CASE_REFERENCE';
type RelationshipType = 'USES_PHONE' | 'USES_EMAIL' | 'ASSOCIATED_WITH_IP' | 'USES_UPI' | 'USES_DEVICE' | 'CONNECTED_TO' | 'APPEARS_IN_CASE' | 'MENTIONED_WITH' | 'LOCATED_AT' | 'MEMBER_OF' | 'OWNS_PHONE' | 'TRANSFERRED_TO';

const ALL_ENTITY_TYPES: EntityType[] = ['PERSON','PHONE','EMAIL','IP_ADDRESS','UPI_ID','BANK_ACCOUNT','VEHICLE','DEVICE','LOCATION','ORGANIZATION','SOCIAL_ACCOUNT','URL','CASE_REFERENCE'];

export default function InvestigationPage() {
  const { id: caseId } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  // Filter state
  const [selectedEntityTypes, setSelectedEntityTypes] = useState<Set<string>>(new Set());
  const [selectedRelTypes, setSelectedRelTypes] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(true);
  const [activeTab, setActiveTab] = useState<'timeline' | 'correlations' | 'leads' | 'patterns'>('timeline');

  // Fetch graph data
  const { data: graphData, isLoading: graphLoading } = useQuery({
    queryKey: ['graph', caseId],
    queryFn: () => api.get(`/api/v1/cases/${caseId}/relationships/graph`).then((r: any) => r.data),
    enabled: !!caseId,
  });

  // Fetch case info
  const { data: caseInfo } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => api.get(`/api/v1/cases/${caseId}`).then((r: any) => r.data),
    enabled: !!caseId,
  });

  // Fetch key entities
  const { data: keyEntities } = useQuery({
    queryKey: ['keyEntities', caseId],
    queryFn: () => api.get(`/api/v1/cases/${caseId}/analysis/key-entities`).then((r: any) => r.data),
    enabled: !!caseId,
  });

  // Fetch patterns
  const { data: patterns } = useQuery({
    queryKey: ['patterns', caseId],
    queryFn: () => api.post(`/api/v1/cases/${caseId}/analysis/patterns`).then((r: any) => r.data.patterns || []),
    enabled: !!caseId,
  });

  // Fetch correlations/leads
  const { data: correlations } = useQuery({
    queryKey: ['correlations', caseId],
    queryFn: () => api.get(`/api/v1/cases/${caseId}/analysis/correlations`).then((r: any) => r.data),
    enabled: !!caseId,
  });

  // Fetch leads
  const { data: leads } = useQuery({
    queryKey: ['leads', caseId],
    queryFn: () => api.get(`/api/v1/leads?case_id=${caseId}`).then((r: any) => r.data),
    enabled: !!caseId,
  });

  // Fetch timeline
  const { data: timeline } = useQuery({
    queryKey: ['timeline', caseId],
    queryFn: () => api.get(`/api/v1/cases/${caseId}/analysis/timeline`).then((r: any) => r.data),
    enabled: !!caseId,
  });

  // Fetch entity detail when selected
  const { data: entityDetail } = useQuery({
    queryKey: ['entity', selectedNodeId],
    queryFn: () => api.get(`/api/v1/entities/${selectedNodeId}`).then((r: any) => r.data),
    enabled: !!selectedNodeId,
  });

  const { data: entityCases } = useQuery({
    queryKey: ['entityCases', selectedNodeId],
    queryFn: () => api.get(`/api/v1/entities/${selectedNodeId}/cases`).then((r: any) => r.data),
    enabled: !!selectedNodeId,
  });

  const { data: entityEvidence } = useQuery({
    queryKey: ['entityEvidence', selectedNodeId],
    queryFn: () => api.get(`/api/v1/entities/${selectedNodeId}/evidence`).then((r: any) => r.data),
    enabled: !!selectedNodeId,
  });

  // Entity correction mutation
  const correctMutation = useMutation({
    mutationFn: (data: { entityId: string; display_value?: string; reason: string }) =>
      api.put(`/api/v1/entities/${data.entityId}/correct`, { display_value: data.display_value, reason: data.reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity', selectedNodeId] });
      queryClient.invalidateQueries({ queryKey: ['graph', caseId] });
    },
  });

  // Filter graph data
  const filteredNodes = (graphData?.nodes || []).filter((n: any) => {
    if (selectedEntityTypes.size > 0 && !selectedEntityTypes.has(n.entity_type)) return false;
    if (searchQuery && !n.label.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const filteredNodeIds = new Set(filteredNodes.map((n: any) => n.id));
  const filteredEdges = (graphData?.edges || []).filter((e: any) => {
    if (selectedRelTypes.size > 0 && !selectedRelTypes.has(e.relationship_type)) return false;
    return filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target);
  });

  const toggleEntityType = (t: string) => {
    setSelectedEntityTypes(prev => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t); else next.add(t);
      return next;
    });
  };

  const toggleRelType = (t: string) => {
    setSelectedRelTypes(prev => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t); else next.add(t);
      return next;
    });
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b px-4 py-3 flex items-center gap-4">
        <Link to={`/cases/${caseId}`} className="text-gray-500 hover:text-gray-700">
          ← Back
        </Link>
        <div className="flex-1">
          <h1 className="text-lg font-semibold">
            {caseInfo?.case_number || 'Loading...'} — Investigation Workspace
          </h1>
          {caseInfo && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              caseInfo.priority === 'CRITICAL' ? 'bg-red-100 text-red-700' :
              caseInfo.priority === 'HIGH' ? 'bg-orange-100 text-orange-700' :
              'bg-gray-100 text-gray-700'
            }`}>{caseInfo.priority}</span>
          )}
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Network size={16} />
          {filteredNodes.length} nodes · {filteredEdges.length} edges
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar — Filters */}
        {showFilters && (
          <div className="w-64 bg-white dark:bg-gray-800 border-r p-4 overflow-y-auto flex-shrink-0">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm">Filters</h3>
              <button onClick={() => setShowFilters(false)} className="text-gray-400 hover:text-gray-600">
                <X size={14} />
              </button>
            </div>

            {/* Search */}
            <div className="relative mb-4">
              <Search size={14} className="absolute left-2 top-2.5 text-gray-400" />
              <input
                type="text"
                placeholder="Search nodes..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-7 pr-2 py-1.5 text-sm border rounded-md bg-gray-50 dark:bg-gray-700"
              />
            </div>

            {/* Entity types */}
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Entity Types</h4>
              {ALL_ENTITY_TYPES.map(t => {
                const count = (graphData?.nodes || []).filter((n: any) => n.entity_type === t).length;
                if (count === 0) return null;
                return (
                  <label key={t} className="flex items-center gap-2 py-1 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 rounded px-1">
                    <input type="checkbox" checked={selectedEntityTypes.has(t)} onChange={() => toggleEntityType(t)} className="rounded" />
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: ENTITY_COLORS[t] || '#999' }} />
                    <span className="flex-1 truncate">{t.replace('_', ' ')}</span>
                    <span className="text-xs text-gray-400">{count}</span>
                  </label>
                );
              })}
            </div>

            {/* Relationship types */}
            <div className="mb-4">
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Relationship Types</h4>
              {['SHARED_IDENTIFIER', 'TEXTUAL_CO_OCCURRENCE', 'CROSS_CASE_LINK', 'TEMPORAL_ASSOCIATION', 'MANUAL'].map(t => {
                const count = (graphData?.edges || []).filter((e: any) => e.relationship_type === t).length;
                if (count === 0) return null;
                return (
                  <label key={t} className="flex items-center gap-2 py-1 text-sm cursor-pointer hover:bg-gray-50 rounded px-1">
                    <input type="checkbox" checked={selectedRelTypes.has(t)} onChange={() => toggleRelType(t)} className="rounded" />
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: REL_COLORS[t] || '#999' }} />
                    <span className="flex-1 truncate text-xs">{t.replace(/_/g, ' ').toLowerCase()}</span>
                    <span className="text-xs text-gray-400">{count}</span>
                  </label>
                );
              })}
            </div>

            {(selectedEntityTypes.size > 0 || selectedRelTypes.size > 0 || searchQuery) && (
              <button
                onClick={() => { setSelectedEntityTypes(new Set()); setSelectedRelTypes(new Set()); setSearchQuery(''); }}
                className="text-xs text-blue-600 hover:underline"
              >Clear all filters</button>
            )}
          </div>
        )}

        {/* Center — Graph */}
        <div className="flex-1 relative">
          {!showFilters && (
            <button onClick={() => setShowFilters(true)} className="absolute top-2 left-2 z-10 bg-white shadow rounded p-1.5 hover:bg-gray-50">
              <Filter size={16} />
            </button>
          )}

          {graphLoading ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 border-t-blue-600" />
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Network size={48} className="mb-4 text-gray-300" />
              <p className="text-lg font-medium">No network data available</p>
              <p className="text-sm">Add or ingest evidence to build the network.</p>
            </div>
          ) : (
            (() => {
              const filteredGraph = {
                nodes: filteredNodes.map((n: any) => ({
                  id: n.id,
                  label: n.label,
                  entity_type: n.entity_type,
                  confidence: n.confidence || 0,
                  degree: n.degree || 0,
                  betweenness: n.betweenness || 0,
                  closeness: n.closeness || 0,
                  cases: n.cases || [],
                })),
                edges: filteredEdges.map((e: any) => ({
                  id: e.id,
                  source: e.source,
                  target: e.target,
                  relationship_type: e.relationship_type,
                  confidence: e.confidence || 0,
                  label: e.relationship_type,
                })),
                stats: { node_count: filteredNodes.length, edge_count: filteredEdges.length },
              };
              return (
                <CytoscapeComponent
                  graph={filteredGraph}
                  onSelectNode={(node: any) => { setSelectedNodeId(node.id); setSelectedEdgeId(null); }}
                  onSelectEdge={(edge: any) => { setSelectedEdgeId(edge.id); setSelectedNodeId(null); }}
                />
              );
            })()
          )}
        </div>

        {/* Right sidebar — Inspector */}
        <div className="w-80 bg-white dark:bg-gray-800 border-l overflow-y-auto flex-shrink-0">
          {/* Node inspection */}
          {selectedNodeId && entityDetail && (
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm">Entity Inspector</h3>
                <button onClick={() => setSelectedNodeId(null)} className="text-gray-400 hover:text-gray-600">
                  <X size={14} />
                </button>
              </div>

              <div className="flex items-center gap-2 mb-3">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: ENTITY_COLORS[entityDetail.entity_type] || '#999' }} />
                <span className="text-xs font-medium text-gray-500">{entityDetail.entity_type}</span>
              </div>

              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 mb-3">
                <p className="font-semibold text-sm">{entityDetail.display_value}</p>
                <p className="text-xs text-gray-500 mt-1">Normalized: {entityDetail.normalized_value}</p>
                <p className="text-xs text-gray-500">Confidence: {(entityDetail.confidence * 100).toFixed(0)}%</p>
              </div>

              {/* Cases */}
              {entityCases && (
                <div className="mb-3">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">
                    Cases ({entityCases.total_cases})
                  </h4>
                  {entityCases.cases?.map((ce: any) => (
                    <div key={ce.case_id} className="text-xs bg-gray-50 rounded p-2 mb-1">
                      <Link to={`/cases/${ce.case_id}`} className="text-blue-600 hover:underline">
                        {ce.case_id.slice(0, 8)}…
                      </Link>
                      <p className="text-gray-500 mt-0.5">Mention: "{ce.mention_text}"</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Evidence */}
              {entityEvidence && (
                <div className="mb-3">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">
                    Evidence ({entityEvidence.evidence_count})
                  </h4>
                  {entityEvidence.evidence?.map((ev: any) => (
                    <div key={ev.evidence_id} className="text-xs bg-gray-50 rounded p-2 mb-1">
                      <p className="font-mono">{ev.evidence_id.slice(0, 8)}…</p>
                      {ev.mentions?.map((m: any, i: number) => (
                        <p key={i} className="text-gray-500">"{m.raw_text}" ({m.extraction_method})</p>
                      ))}
                    </div>
                  ))}
                </div>
              )}

              {/* Correction form */}
              <div className="border-t pt-3">
                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Correct Entity</h4>
                <form onSubmit={async (e) => {
                  e.preventDefault();
                  const form = new FormData(e.currentTarget);
                  await correctMutation.mutateAsync({
                    entityId: selectedNodeId,
                    display_value: form.get('display_value') as string || undefined,
                    reason: form.get('reason') as string,
                  });
                  (e.target as HTMLFormElement).reset();
                }}>
                  <input name="display_value" placeholder="New display value" className="w-full text-xs border rounded px-2 py-1 mb-2" />
                  <input name="reason" placeholder="Reason (required)" required className="w-full text-xs border rounded px-2 py-1 mb-2" />
                  <button type="submit" className="w-full text-xs bg-blue-600 text-white rounded py-1.5 hover:bg-blue-700" disabled={correctMutation.isPending}>
                    {correctMutation.isPending ? 'Correcting...' : 'Apply Correction'}
                  </button>
                </form>
                <p className="text-[10px] text-gray-400 mt-1">Original evidence text is never modified.</p>
              </div>
            </div>
          )}

          {/* Edge inspection */}
          {selectedEdgeId && graphData && (
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm">Relationship Inspector</h3>
                <button onClick={() => setSelectedEdgeId(null)} className="text-gray-400 hover:text-gray-600">
                  <X size={14} />
                </button>
              </div>
              {(() => {
                const edge = graphData.edges.find((e: any) => e.id === selectedEdgeId);
                if (!edge) return <p className="text-sm text-gray-500">Edge not found</p>;
                return (
                  <div className="space-y-3">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500">Type</p>
                      <p className="text-sm font-semibold">{edge.relationship_type?.replace(/_/g, ' ')}</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500">Confidence</p>
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                        <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${(edge.confidence || 0) * 100}%` }} />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{((edge.confidence || 0) * 100).toFixed(0)}%</p>
                    </div>
                    <div className="text-xs text-gray-500">
                      <p>Source: {edge.source?.slice(0, 8)}…</p>
                      <p>Target: {edge.target?.slice(0, 8)}…</p>
                      {edge.label && <p>Label: {edge.label}</p>}
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* Default state — Key entities + patterns */}
          {!selectedNodeId && !selectedEdgeId && (
            <div className="p-4">
              <h3 className="font-semibold text-sm mb-3">Key Entities</h3>
              {keyEntities && keyEntities.length > 0 ? (
                <div className="space-y-2">
                  {keyEntities.slice(0, 10).map((ke: any, i: number) => (
                    <button
                      key={ke.entity_id}
                      onClick={() => setSelectedNodeId(ke.entity_id)}
                      className="w-full text-left bg-gray-50 hover:bg-gray-100 rounded-lg p-2 transition"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-gray-400 w-5">#{i + 1}</span>
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: ENTITY_COLORS[ke.entity_type] || '#999' }} />
                        <span className="text-xs font-medium truncate flex-1">{ke.label}</span>
                        <span className="text-xs text-gray-500">{ke.score?.toFixed(0)}</span>
                      </div>
                      <div className="flex gap-3 ml-7 text-[10px] text-gray-500 mt-1">
                        <span>D:{ke.factors?.degree?.toFixed(0)}</span>
                        <span>B:{ke.factors?.betweenness?.toFixed(0)}</span>
                        <span>X:{ke.factors?.cross_case?.toFixed(0)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500">No key entities detected.</p>
              )}

              {/* Pattern alerts */}
              {patterns && patterns.length > 0 && (
                <div className="mt-4">
                  <h3 className="font-semibold text-sm mb-2">Pattern Alerts</h3>
                  <div className="space-y-2">
                    {patterns.slice(0, 5).map((p: any, i: number) => (
                      <div key={i} className="bg-amber-50 border border-amber-200 rounded-lg p-2">
                        <div className="flex items-center gap-1">
                          <AlertTriangle size={12} className="text-amber-600" />
                          <span className="text-xs font-semibold text-amber-800">{p.pattern_type?.replace(/_/g, ' ')}</span>
                        </div>
                        <p className="text-[10px] text-amber-700 mt-1">{p.explanation?.slice(0, 120)}…</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bottom panel — Timeline / Leads / Correlations */}
      <div className="bg-white dark:bg-gray-800 border-t h-48 flex flex-col">
        <div className="flex border-b">
          {(['timeline', 'leads', 'correlations', 'patterns'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-xs font-medium capitalize border-b-2 transition ${
                activeTab === tab ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'patterns' && patterns && patterns.length > 0 && (
                <span className="mr-1 bg-amber-500 text-white text-[10px] px-1 rounded-full">{patterns.length}</span>
              )}
              {tab}
            </button>
          ))}
          <div className="flex-1" />
          <Link to={`/cases/${caseId}`} className="px-4 py-2 text-xs text-gray-500 hover:text-gray-700">
            Case Overview →
          </Link>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {activeTab === 'timeline' && (
            <div className="space-y-2">
              {timeline?.events?.length > 0 ? timeline.events.slice(0, 20).map((ev: any, i: number) => (
                <div key={i} className="flex items-start gap-3 text-xs">
                  <span className="text-gray-400 w-32 flex-shrink-0 font-mono">
                    {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : 'No timestamp'}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                    ev.event_type === 'ENTITY_MENTIONED' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{ev.event_type?.replace(/_/g, ' ')}</span>
                  <span className="text-gray-600">{ev.raw_text || ev.description}</span>
                </div>
              )) : <p className="text-xs text-gray-500">No timeline events.</p>}
            </div>
          )}

          {activeTab === 'leads' && (
            <div className="space-y-2">
              {leads?.items?.length > 0 ? leads.items.map((lead: any) => (
                <Link
                  key={lead.id}
                  to={`/leads/${lead.id}`}
                  className="flex items-center gap-3 p-2 rounded hover:bg-gray-50 text-xs"
                >
                  <span className={`w-2 h-2 rounded-full ${
                    lead.priority === 'CRITICAL' ? 'bg-red-500' :
                    lead.priority === 'HIGH' ? 'bg-orange-500' :
                    lead.priority === 'MEDIUM' ? 'bg-yellow-500' : 'bg-gray-300'
                  }`} />
                  <span className="flex-1 truncate">{lead.explanation?.slice(0, 80)}</span>
                  <span className="font-mono text-gray-500">{lead.score?.toFixed(0)}/100</span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                    lead.status === 'CONFIRMED' ? 'bg-green-100 text-green-700' :
                    lead.status === 'REVIEWING' ? 'bg-blue-100 text-blue-700' :
                    lead.status === 'DISMISSED' ? 'bg-gray-100 text-gray-500' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>{lead.status}</span>
                </Link>
              )) : <p className="text-xs text-gray-500">No leads found.</p>}
            </div>
          )}

          {activeTab === 'correlations' && (
            <div className="space-y-2">
              {correlations?.correlations?.length > 0 ? correlations.correlations.map((c: any, i: number) => (
                <div key={i} className="p-2 bg-gray-50 rounded text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-mono">{c.related_case_number || c.related_case_id?.slice(0, 8)}</span>
                    <span className="font-semibold">Score: {c.score?.toFixed(0)}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                      c.priority === 'VERY_HIGH' || c.priority === 'HIGH' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
                    }`}>{c.priority}</span>
                  </div>
                  <p className="text-gray-500 mt-1">{c.explanation?.slice(0, 120)}</p>
                </div>
              )) : <p className="text-xs text-gray-500">No correlations found. Run correlation analysis first.</p>}
            </div>
          )}

          {activeTab === 'patterns' && (
            <div className="space-y-2">
              {patterns?.length > 0 ? patterns.map((p: any, i: number) => (
                <div key={i} className="p-2 bg-amber-50 border border-amber-200 rounded text-xs">
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={12} className="text-amber-600" />
                    <span className="font-semibold text-amber-800">{p.pattern_type?.replace(/_/g, ' ')}</span>
                    <span className="text-amber-600">Observed: {p.observed_value} (threshold: {p.threshold})</span>
                  </div>
                  <p className="text-amber-700 mt-1">{p.explanation}</p>
                </div>
              )) : <p className="text-xs text-gray-500">No patterns detected.</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
