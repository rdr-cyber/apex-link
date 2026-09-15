import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, AlertTriangle, CheckCircle, XCircle, Clock, Eye, Shield, FileText, Link2, MessageSquare } from 'lucide-react'
import { api } from '../api'

const PRIORITY_BADGE: Record<string, string> = {
  CRITICAL: 'badge-critical', HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low',
}

const STATUS_STYLE: Record<string, string> = {
  NEW: 'bg-crosscase/10 text-crosscase border border-crosscase/20',
  REVIEWING: 'bg-dossier/10 text-dossier-dim border border-dossier/20',
  CONFIRMED: 'bg-field/10 text-field border border-field/20',
  DISMISSED: 'bg-gray-100 text-gray-500 border border-mist-dark',
}

export default function LeadDetailPage() {
  const { id: leadId } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [reviewNote, setReviewNote] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)
  const [showDismiss, setShowDismiss] = useState(false)

  const { data: lead, isLoading } = useQuery({
    queryKey: ['lead', leadId],
    queryFn: () => api.get(`/api/v1/leads/${leadId}`).then((r: any) => r.data),
    enabled: !!leadId,
  })

  const reviewMutation = useMutation({
    mutationFn: (data: { status: string; review_notes: string }) =>
      api.put(`/api/v1/leads/${leadId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] })
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      setReviewNote(''); setShowConfirm(false); setShowDismiss(false)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-6 w-6 border-2 border-mist-dark border-t-dossier" />
      </div>
    )
  }

  if (!lead) {
    return <div className="card"><p className="text-xs text-gray-400">Lead not found.</p></div>
  }

  const factors = typeof lead.factors === 'string' ? JSON.parse(lead.factors || '[]') : (lead.factors || [])
  const totalScore = factors.reduce((sum: number, f: any) => sum + (f.weight || 0), 0)

  const statusTransitions: Record<string, string[]> = {
    NEW: ['REVIEWING'], REVIEWING: ['CONFIRMED', 'DISMISSED'],
    CONFIRMED: [], DISMISSED: ['REVIEWING'],
  }
  const allowedTransitions = statusTransitions[lead.status] || []

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-mist-dark pb-3">
        <Link to="/leads" className="rounded p-1 hover:bg-cream-dark transition-colors">
          <ArrowLeft className="h-4 w-4 text-gray-500" />
        </Link>
        <div className="flex-1">
          <h1 className="text-lg font-bold text-ink font-mono tracking-wide">ANALYTICAL LEAD</h1>
          <p className="text-[10px] text-gray-400 font-mono">ID: {lead.id?.slice(0, 8)}…</p>
        </div>
        <span className={`badge ${PRIORITY_BADGE[lead.priority] || 'badge'}`}>{lead.priority}</span>
        <span className={`badge ${STATUS_STYLE[lead.status] || 'badge'}`}>{lead.status}</span>
      </div>

      {/* Score */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="h-4 w-4 text-dossier" />
          <h2 className="text-sm font-bold font-mono text-ink">CORRELATION SCORE</h2>
        </div>
        <div className="flex items-center gap-4 mb-3">
          <div className="text-center">
            <div className="font-mono text-4xl font-extrabold text-dossier leading-none">{lead.score?.toFixed(0)}</div>
            <div className="text-[10px] text-gray-400 font-mono">/ 100</div>
          </div>
          <div className="flex-1">
            {factors.length > 0 ? (
              <div className="space-y-1">
                {factors.map((f: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="w-36 text-gray-500 truncate">{f.type?.replace(/_/g, ' ').toLowerCase() || f.description}</span>
                    <div className="flex-1 bg-mist rounded-full h-1">
                      <div className="bg-dossier h-1 rounded-full" style={{ width: `${Math.min(100, (f.weight || f.contribution || 0))}%` }} />
                    </div>
                    <span className="w-10 text-right font-mono text-gray-500">+{f.weight || f.contribution || 0}</span>
                  </div>
                ))}
                <div className="border-t border-mist-dark pt-1 flex items-center gap-2 text-xs font-semibold">
                  <span className="w-36 text-ink">Total</span>
                  <span className="flex-1" />
                  <span className="w-10 text-right font-mono text-dossier">{totalScore || lead.score?.toFixed(0)}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-gray-500 font-mono">Score: {lead.score?.toFixed(0)}/100</p>
            )}
          </div>
        </div>
        <div className="p-2.5 rounded bg-dossier/5 border border-dossier/15 text-xs text-dossier-dim font-mono">
          This score represents an analytical correlation signal. It is not a measure of guilt and requires investigator review.
        </div>
      </div>

      {/* Explanation */}
      <div className="card">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="h-4 w-4 text-crosscase" />
          <h2 className="text-sm font-bold font-mono text-ink">EXPLANATION</h2>
        </div>
        <p className="text-xs text-gray-600 whitespace-pre-wrap leading-relaxed">{lead.explanation}</p>
      </div>

      {/* Cases */}
      <div className="card">
        <div className="flex items-center gap-2 mb-2">
          <Link2 className="h-4 w-4 text-crosscase" />
          <h2 className="text-sm font-bold font-mono text-ink">CASES</h2>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded bg-cream-dark border border-mist-dark">
            <p className="text-label text-gray-400">Primary Case</p>
            <Link to={`/cases/${lead.case_id}`} className="text-crosscase hover:underline text-xs font-mono">
              {lead.case_id?.slice(0, 8)}…
            </Link>
          </div>
          {lead.related_case_id && (
            <div className="p-3 rounded bg-cream-dark border border-mist-dark">
              <p className="text-label text-gray-400">Related Case</p>
              <Link to={`/cases/${lead.related_case_id}`} className="text-crosscase hover:underline text-xs font-mono">
                {lead.related_case_id?.slice(0, 8)}…
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Algorithm details */}
      <div className="card">
        <div className="flex items-center gap-2 mb-2">
          <Eye className="h-4 w-4 text-gray-400" />
          <h2 className="text-sm font-bold font-mono text-ink">ALGORITHM DETAILS</h2>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <div><span className="text-gray-400">Lead type:</span> <span className="text-ink">{lead.lead_type}</span></div>
          <div><span className="text-gray-400">Version:</span> <span className="text-ink">{lead.algorithm_version || '1.0.0'}</span></div>
          <div><span className="text-gray-400">Created:</span> <span className="text-ink">{lead.created_at ? new Date(lead.created_at).toLocaleString() : 'N/A'}</span></div>
          {lead.reviewed_by && <div><span className="text-gray-400">Reviewed by:</span> <span className="text-ink">{lead.reviewed_by?.slice(0, 8)}…</span></div>}
          {lead.reviewed_at && <div><span className="text-gray-400">Reviewed at:</span> <span className="text-ink">{new Date(lead.reviewed_at).toLocaleString()}</span></div>}
        </div>
        {lead.review_notes && (
          <div className="mt-2 p-2.5 rounded bg-cream-dark border border-mist-dark">
            <p className="text-label text-gray-400 mb-1">Review Notes</p>
            <p className="text-xs text-ink">{lead.review_notes}</p>
          </div>
        )}
      </div>

      {/* Review controls */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <MessageSquare className="h-4 w-4 text-gray-400" />
          <h2 className="text-sm font-bold font-mono text-ink">REVIEW</h2>
        </div>
        <textarea
          value={reviewNote}
          onChange={e => setReviewNote(e.target.value)}
          placeholder="Add review notes..."
          className="input-field text-xs mb-2"
          rows={3}
        />
        <div className="flex gap-2">
          {allowedTransitions.includes('REVIEWING') && (
            <button
              onClick={() => reviewMutation.mutate({ status: 'REVIEWING', review_notes: reviewNote })}
              disabled={reviewMutation.isPending}
              className="btn-secondary text-xs"
            >
              <Clock className="h-3.5 w-3.5 mr-1" /> Mark Reviewing
            </button>
          )}
          {allowedTransitions.includes('CONFIRMED') && (
            <>
              {showConfirm ? (
                <div className="flex gap-1.5">
                  <button
                    onClick={() => reviewMutation.mutate({ status: 'CONFIRMED', review_notes: reviewNote || 'Confirmed' })}
                    disabled={reviewMutation.isPending}
                    className="btn-primary text-xs"
                  >
                    <CheckCircle className="h-3.5 w-3.5 mr-1" /> Confirm Lead
                  </button>
                  <button onClick={() => setShowConfirm(false)} className="btn-ghost text-xs">Cancel</button>
                </div>
              ) : (
                <button onClick={() => setShowConfirm(true)} className="btn-primary text-xs">
                  <CheckCircle className="h-3.5 w-3.5 mr-1" /> Confirm
                </button>
              )}
            </>
          )}
          {allowedTransitions.includes('DISMISSED') && (
            <>
              {showDismiss ? (
                <div className="flex gap-1.5">
                  <button
                    onClick={() => reviewMutation.mutate({ status: 'DISMISSED', review_notes: reviewNote || 'Dismissed' })}
                    disabled={reviewMutation.isPending}
                    className="btn-danger text-xs"
                  >
                    <XCircle className="h-3.5 w-3.5 mr-1" /> Dismiss Lead
                  </button>
                  <button onClick={() => setShowDismiss(false)} className="btn-ghost text-xs">Cancel</button>
                </div>
              ) : (
                <button onClick={() => setShowDismiss(true)} className="btn-secondary text-xs">
                  <XCircle className="h-3.5 w-3.5 mr-1" /> Dismiss
                </button>
              )}
            </>
          )}
        </div>
        {allowedTransitions.length === 0 && (
          <p className="text-[10px] text-gray-400 mt-2 font-mono">Lead has been {lead.status.toLowerCase()}. No further actions.</p>
        )}
      </div>

      {/* Disclaimer */}
      <div className="p-3 rounded border border-dossier/20 bg-dossier/5">
        <p className="text-[10px] text-dossier-dim font-mono">
          <AlertTriangle className="h-3 w-3 inline mr-1" />
          Analytical results are potential investigative leads requiring human verification.
        </p>
      </div>
    </div>
  )
}
