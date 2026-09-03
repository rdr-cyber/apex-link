import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, AlertTriangle, CheckCircle, XCircle, Clock,
  Eye, Shield, FileText, Link2, MessageSquare
} from 'lucide-react';
import { api } from '../api';

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700', HIGH: 'bg-orange-100 text-orange-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700', LOW: 'bg-gray-100 text-gray-600',
};

const STATUS_COLORS: Record<string, string> = {
  NEW: 'bg-yellow-100 text-yellow-700', REVIEWING: 'bg-blue-100 text-blue-700',
  CONFIRMED: 'bg-green-100 text-green-700', DISMISSED: 'bg-gray-200 text-gray-600',
};

export default function LeadDetailPage() {
  const { id: leadId } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [reviewNote, setReviewNote] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);
  const [showDismiss, setShowDismiss] = useState(false);

  const { data: lead, isLoading } = useQuery({
    queryKey: ['lead', leadId],
    queryFn: () => api.get(`/api/v1/leads/${leadId}`).then((r: any) => r.data),
    enabled: !!leadId,
  });

  const reviewMutation = useMutation({
    mutationFn: (data: { status: string; review_notes: string }) =>
      api.put(`/api/v1/leads/${leadId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      setReviewNote('');
      setShowConfirm(false);
      setShowDismiss(false);
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 border-t-blue-600" />
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
        <p className="text-gray-500">Lead not found.</p>
      </div>
    );
  }

  const factors = typeof lead.factors === 'string' ? JSON.parse(lead.factors || '[]') : (lead.factors || []);
  const totalScore = factors.reduce((sum: number, f: any) => sum + (f.weight || 0), 0);

  const statusTransitions: Record<string, string[]> = {
    NEW: ['REVIEWING'], REVIEWING: ['CONFIRMED', 'DISMISSED'],
    CONFIRMED: [], DISMISSED: ['REVIEWING'],
  };
  const allowedTransitions = statusTransitions[lead.status] || [];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link to="/leads" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex-1">
            <h1 className="text-xl font-bold">Analytical Lead</h1>
            <p className="text-sm text-gray-500">ID: {lead.id?.slice(0, 8)}…</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[lead.status] || ''}`}>
            {lead.status}
          </span>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${PRIORITY_COLORS[lead.priority] || ''}`}>
            {lead.priority}
          </span>
        </div>

        {/* Score explanation */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Shield size={18} /> Correlation Score
          </h2>

          <div className="flex items-center gap-6 mb-4">
            <div className="text-center">
              <div className="text-4xl font-bold text-blue-600">{lead.score?.toFixed(0)}</div>
              <div className="text-xs text-gray-500">/ 100</div>
            </div>
            <div className="flex-1">
              {factors.length > 0 ? (
                <div className="space-y-1">
                  {factors.map((f: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span className="w-40 text-gray-600">{f.type?.replace(/_/g, ' ').toLowerCase() || f.description}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                        <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${(f.weight || f.contribution || 0)}%` }} />
                      </div>
                      <span className="w-12 text-right font-mono text-gray-500">+{f.weight || f.contribution || 0}</span>
                    </div>
                  ))}
                  <div className="border-t pt-1 flex items-center gap-2 text-sm font-semibold">
                    <span className="w-40">Calculated result</span>
                    <span className="flex-1" />
                    <span className="w-12 text-right">{totalScore || lead.score?.toFixed(0)}</span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-500">Score: {lead.score?.toFixed(0)}/100</p>
              )}
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700">
            This score represents an analytical correlation signal generated from available data. It is not a measure of guilt or criminal responsibility and requires investigator review.
          </div>
        </div>

        {/* Explanation */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            <FileText size={18} /> Explanation
          </h2>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{lead.explanation}</p>
        </div>

        {/* Cases */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            <Link2 size={18} /> Cases
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500 mb-1">Primary Case</p>
              <Link to={`/cases/${lead.case_id}`} className="text-blue-600 hover:underline text-sm font-mono">
                {lead.case_id?.slice(0, 8)}…
              </Link>
            </div>
            {lead.related_case_id && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-xs text-gray-500 mb-1">Related Case</p>
                <Link to={`/cases/${lead.related_case_id}`} className="text-blue-600 hover:underline text-sm font-mono">
                  {lead.related_case_id?.slice(0, 8)}…
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Algorithm details */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            <Eye size={18} /> Algorithm Details
          </h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><span className="text-gray-500">Lead type:</span> {lead.lead_type}</div>
            <div><span className="text-gray-500">Algorithm version:</span> {lead.algorithm_version || '1.0.0'}</div>
            <div><span className="text-gray-500">Created:</span> {lead.created_at ? new Date(lead.created_at).toLocaleString() : 'N/A'}</div>
            {lead.reviewed_by && (
              <div><span className="text-gray-500">Reviewed by:</span> {lead.reviewed_by?.slice(0, 8)}…</div>
            )}
            {lead.reviewed_at && (
              <div><span className="text-gray-500">Reviewed at:</span> {new Date(lead.reviewed_at).toLocaleString()}</div>
            )}
          </div>
          {lead.review_notes && (
            <div className="mt-3 bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Review Notes</p>
              <p className="text-sm">{lead.review_notes}</p>
            </div>
          )}
        </div>

        {/* Review controls */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            <MessageSquare size={18} /> Review Controls
          </h2>

          <div className="mb-3">
            <textarea
              value={reviewNote}
              onChange={e => setReviewNote(e.target.value)}
              placeholder="Add review notes (optional for reviewing, required for confirm/dismiss)..."
              className="w-full border rounded-lg p-2 text-sm"
              rows={3}
            />
          </div>

          <div className="flex gap-3">
            {allowedTransitions.includes('REVIEWING') && (
              <button
                onClick={() => reviewMutation.mutate({ status: 'REVIEWING', review_notes: reviewNote })}
                disabled={reviewMutation.isPending}
                className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                <Clock size={14} /> Mark Reviewing
              </button>
            )}
            {allowedTransitions.includes('CONFIRMED') && (
              <>
                {showConfirm ? (
                  <div className="flex gap-2">
                    <button
                      onClick={() => reviewMutation.mutate({ status: 'CONFIRMED', review_notes: reviewNote || 'Confirmed by investigator' })}
                      disabled={reviewMutation.isPending}
                      className="flex items-center gap-1 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
                    >
                      <CheckCircle size={14} /> Confirm Lead
                    </button>
                    <button onClick={() => setShowConfirm(false)} className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700">Cancel</button>
                  </div>
                ) : (
                  <button onClick={() => setShowConfirm(true)} className="flex items-center gap-1 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
                    <CheckCircle size={14} /> Confirm
                  </button>
                )}
              </>
            )}
            {allowedTransitions.includes('DISMISSED') && (
              <>
                {showDismiss ? (
                  <div className="flex gap-2">
                    <button
                      onClick={() => reviewMutation.mutate({ status: 'DISMISSED', review_notes: reviewNote || 'Dismissed by investigator' })}
                      disabled={reviewMutation.isPending}
                      className="flex items-center gap-1 px-4 py-2 bg-gray-600 text-white rounded-lg text-sm hover:bg-gray-700"
                    >
                      <XCircle size={14} /> Dismiss Lead
                    </button>
                    <button onClick={() => setShowDismiss(false)} className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700">Cancel</button>
                  </div>
                ) : (
                  <button onClick={() => setShowDismiss(true)} className="flex items-center gap-1 px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                    <XCircle size={14} /> Dismiss
                  </button>
                )}
              </>
            )}
          </div>

          {allowedTransitions.length === 0 && (
            <p className="text-xs text-gray-400 mt-2">This lead has been {lead.status.toLowerCase()}. No further actions available.</p>
          )}
        </div>

        {/* Disclaimer */}
        <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
          <AlertTriangle size={14} className="inline mr-1" />
          Analytical results are potential investigative leads generated from available data. They require human verification and do not establish criminal responsibility.
        </div>
      </div>
    </div>
  );
}
