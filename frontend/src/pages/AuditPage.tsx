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
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <div className="card">
          <p className="text-sm text-red-600">
            Access denied. Audit logs are available to administrators only.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ScrollText className="h-6 w-6 text-trace-600" />
        <h1 className="text-2xl font-bold">Audit Log</h1>
      </div>

      {isLoading ? (
        <div className="card animate-pulse space-y-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-12 rounded bg-gray-200 dark:bg-gray-700" />
          ))}
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800 text-left text-xs font-medium uppercase text-gray-500">
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Details</th>
                <th className="px-4 py-3">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {data?.items?.map((log: any) => (
                <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-xs font-mono text-gray-500">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className="badge bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {log.resource_type}
                    {log.resource_id && <span className="font-mono text-xs ml-1">({log.resource_id.substring(0, 8)}...)</span>}
                  </td>
                  <td className="px-4 py-3 text-sm max-w-xs truncate">{log.details}</td>
                  <td className="px-4 py-3 text-xs font-mono text-gray-400">{log.ip_address || '—'}</td>
                </tr>
              ))}
              {data?.items?.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-sm text-gray-500">
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
