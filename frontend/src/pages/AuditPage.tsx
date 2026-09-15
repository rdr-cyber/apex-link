import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { auditApi } from '@/api'
import { ScrollText } from 'lucide-react'

export function AuditPage() {
  const [page, setPage] = useState(1)

  const { data, isLoading, error } = useQuery({
    queryKey: ['audit', page],
    queryFn: () => auditApi.list({ page, page_size: 50 }).then((r) => r.data),
  })

  if (error) {
    return (
      <div className="space-y-5">
        <h1 className="text-lg font-bold text-ink font-mono tracking-wide">AUDIT LOG</h1>
        <div className="card">
          <p className="text-xs text-alert font-mono">
            Access denied. Audit logs are available to administrators only.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-baseline justify-between border-b border-mist-dark pb-3">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-bold text-ink font-mono tracking-wide">AUDIT LOG</h1>
          <ScrollText className="h-4 w-4 text-gray-400" />
        </div>
      </div>

      {isLoading ? (
        <div className="card space-y-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-10 rounded bg-mist" />
          ))}
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-mist-dark text-left">
                <th className="px-3 py-2 text-label text-gray-400">Timestamp</th>
                <th className="px-3 py-2 text-label text-gray-400">Action</th>
                <th className="px-3 py-2 text-label text-gray-400">Resource</th>
                <th className="px-3 py-2 text-label text-gray-400">Details</th>
                <th className="px-3 py-2 text-label text-gray-400">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-mist">
              {data?.items?.map((log: any) => (
                <tr key={log.id} className="table-row-hover">
                  <td className="px-3 py-2 text-[11px] font-mono text-gray-500">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                  </td>
                  <td className="px-3 py-2">
                    <span className="evidence-tag">{log.action}</span>
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500 font-mono">
                    {log.resource_type}
                    {log.resource_id && <span className="text-gray-400 ml-1">({log.resource_id.substring(0, 8)}...)</span>}
                  </td>
                  <td className="px-3 py-2 text-xs max-w-xs truncate text-gray-600">{log.details}</td>
                  <td className="px-3 py-2 text-[11px] font-mono text-gray-400">{log.ip_address || '—'}</td>
                </tr>
              ))}
              {data?.items?.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-12 text-center text-xs text-gray-400 font-mono">
                    No audit logs found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
