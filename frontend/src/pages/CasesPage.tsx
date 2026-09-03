import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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

const statusBadge = (s: string) => {
  const colors: Record<string, string> = {
    OPEN: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    UNDER_REVIEW: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    ANALYSIS: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
    CLOSED: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400',
    ARCHIVED: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-500',
  }
  return <span className={`badge ${colors[s] || ''}`}>{s.replace('_', ' ')}</span>
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Cases</h1>
        <button onClick={() => navigate('/cases/new')} className="btn-primary">
          <Plus className="mr-2 h-4 w-4" /> New Case
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search cases..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
            className="input-field pl-10"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
          className="input-field w-auto"
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
          className="input-field w-auto"
        >
          <option value="">All Priority</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="card animate-pulse space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 rounded bg-gray-200 dark:bg-gray-700" />
          ))}
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800 text-left text-xs font-medium uppercase text-gray-500">
                <th className="px-4 py-3">Case Number</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Location</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {data?.items.map((c) => (
                <tr
                  key={c.id}
                  className="cursor-pointer table-row-hover"
                  onClick={() => navigate(`/cases/${c.id}`)}
                >
                  <td className="px-4 py-3 font-mono text-sm font-medium text-trace-600">{c.case_number}</td>
                  <td className="px-4 py-3 text-sm">{c.title}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{c.category.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-3">{priorityBadge(c.priority)}</td>
                  <td className="px-4 py-3">{statusBadge(c.status)}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{c.location || '—'}</td>
                </tr>
              ))}
              {data?.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-gray-500">
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
          <p className="text-sm text-gray-500">
            Showing {(page - 1) * 15 + 1}–{Math.min(page * 15, data.total)} of {data.total}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-secondary"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page * 15 >= data.total}
              className="btn-secondary"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
