import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { casesApi } from '@/api'
import { Plus, Search, ChevronLeft, ChevronRight } from 'lucide-react'

const priorityBadge = (p: string) => {
  const classes: Record<string, string> = {
    CRITICAL: 'badge-critical',
    HIGH: 'badge-high',
    MEDIUM: 'badge-medium',
    LOW: 'badge-low',
  }
  return <span className={classes[p] || 'badge'}>{p}</span>
}

const statusDot = (s: string) => {
  const colors: Record<string, string> = {
    OPEN: 'status-dot-active',
    UNDER_REVIEW: 'status-dot-warning',
    ANALYSIS: 'bg-crosscase',
    CLOSED: 'bg-gray-400',
    ARCHIVED: 'bg-gray-300',
  }
  return <span className={`status-dot ${colors[s] || 'bg-gray-300'}`} />
}

const statusLabel = (s: string) => {
  return <span className="text-xs font-mono text-gray-500">{s.replace('_', ' ')}</span>
}

export function CasesPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['cases', page, searchQuery, statusFilter, priorityFilter],
    queryFn: () =>
      casesApi
        .list({
          page,
          page_size: 15,
          ...(searchQuery && { query: searchQuery }),
          ...(statusFilter && { status: statusFilter }),
          ...(priorityFilter && { priority: priorityFilter }),
        })
        .then((r) => r.data),
  })

  return (
    <div className="space-y-5">
      <div className="flex items-baseline justify-between border-b border-mist-dark pb-3">
        <h1 className="text-lg font-bold text-ink font-mono tracking-wide">CASES</h1>
        <button onClick={() => navigate('/cases/new')} className="btn-primary text-xs">
          <Plus className="mr-1.5 h-3.5 w-3.5" /> New Case
        </button>
      </div>

      {/* Filters — tight, functional */}
      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[180px]">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search cases..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
            className="input-field pl-8 text-xs"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="input-field w-auto text-xs"
        >
          <option value="">All Status</option>
          <option value="OPEN">Open</option>
          <option value="UNDER_REVIEW">Under Review</option>
          <option value="ANALYSIS">Analysis</option>
          <option value="CLOSED">Closed</option>
          <option value="ARCHIVED">Archived</option>
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

      {/* Table — tight rows, case-file aesthetic */}
      {isLoading ? (
        <div className="card space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 rounded bg-mist" />
          ))}
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-mist-dark text-left">
                <th className="px-3 py-2 text-label text-gray-400">Case #</th>
                <th className="px-3 py-2 text-label text-gray-400">Title</th>
                <th className="px-3 py-2 text-label text-gray-400">Category</th>
                <th className="px-3 py-2 text-label text-gray-400">Priority</th>
                <th className="px-3 py-2 text-label text-gray-400">Status</th>
                <th className="px-3 py-2 text-label text-gray-400">Location</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-mist">
              {data?.items.map((c) => (
                <tr
                  key={c.id}
                  className="cursor-pointer table-row-hover"
                  onClick={() => navigate(`/cases/${c.id}`)}
                >
                  <td className="px-3 py-2.5 case-number">{c.case_number}</td>
                  <td className="px-3 py-2.5 text-sm text-ink">{c.title}</td>
                  <td className="px-3 py-2.5 text-xs font-mono text-gray-500">{c.category.replace(/_/g, ' ')}</td>
                  <td className="px-3 py-2.5">{priorityBadge(c.priority)}</td>
                  <td className="px-3 py-2.5">
                    <span className="flex items-center gap-1.5">
                      {statusDot(c.status)}
                      {statusLabel(c.status)}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-gray-500">{c.location || '—'}</td>
                </tr>
              ))}
              {data?.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-12 text-center text-xs text-gray-400">
                    No cases found. Create your first case to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {data && data.total > 15 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400 font-mono">
            {String((page - 1) * 15 + 1).padStart(2, '0')}–{String(Math.min(page * 15, data.total)).padStart(2, '0')} / {String(data.total).padStart(2, '0')}
          </p>
          <div className="flex gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-secondary text-xs px-2 py-1"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page * 15 >= data.total}
              className="btn-secondary text-xs px-2 py-1"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
