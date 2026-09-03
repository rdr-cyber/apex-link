import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { entitiesApi } from '@/api'
import { Search, Network } from 'lucide-react'

const entityTypeColors: Record<string, string> = {
  PERSON: 'bg-blue-100 text-blue-800',
  PHONE: 'bg-green-100 text-green-800',
  EMAIL: 'bg-purple-100 text-purple-800',
  IP_ADDRESS: 'bg-red-100 text-red-800',
  UPI_ID: 'bg-yellow-100 text-yellow-800',
  VEHICLE: 'bg-orange-100 text-orange-800',
  DEVICE: 'bg-cyan-100 text-cyan-800',
  LOCATION: 'bg-pink-100 text-pink-800',
  ORGANIZATION: 'bg-indigo-100 text-indigo-800',
  BANK_ACCOUNT: 'bg-emerald-100 text-emerald-800',
}

export function EntitiesPage() {
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['entities', page, searchQuery, typeFilter],
    queryFn: () =>
      entitiesApi
        .list({
          page,
          page_size: 20,
          ...(searchQuery && { query: searchQuery }),
          ...(typeFilter && { entity_type: typeFilter }),
        })
        .then((r) => r.data),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Network className="h-6 w-6 text-trace-600" />
        <h1 className="text-2xl font-bold">Entity Explorer</h1>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search entities..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
            className="input-field pl-10"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
          className="input-field w-auto"
        >
          <option value="">All Types</option>
          <option value="PERSON">Person</option>
          <option value="PHONE">Phone</option>
          <option value="EMAIL">Email</option>
          <option value="IP_ADDRESS">IP Address</option>
          <option value="UPI_ID">UPI ID</option>
          <option value="VEHICLE">Vehicle</option>
          <option value="DEVICE">Device</option>
          <option value="LOCATION">Location</option>
          <option value="ORGANIZATION">Organization</option>
          <option value="BANK_ACCOUNT">Bank Account</option>
        </select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card animate-pulse h-24" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {data?.items.map((entity) => (
            <div key={entity.id} className="card">
              <div className="flex items-start justify-between">
                <div>
                  <span className={`badge text-xs ${entityTypeColors[entity.entity_type] || 'bg-gray-100 text-gray-800'}`}>
                    {entity.entity_type}
                  </span>
                  <p className="mt-2 font-medium">{entity.display_value}</p>
                </div>
                <div className="text-right text-xs text-gray-400">
                  <p>Confidence: {(entity.confidence * 100).toFixed(0)}%</p>
                </div>
              </div>
            </div>
          ))}
          {data?.items.length === 0 && (
            <div className="col-span-full card text-center py-12">
              <p className="text-sm text-gray-500">No entities found.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
