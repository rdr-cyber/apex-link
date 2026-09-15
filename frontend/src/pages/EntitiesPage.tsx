import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { entitiesApi } from '@/api'
import { Search, Network } from 'lucide-react'

const entityTypeColors: Record<string, string> = {
  PERSON: 'bg-node-person/15 text-node-person border border-node-person/20',
  PHONE: 'bg-node-phone/15 text-node-phone border border-node-phone/20',
  EMAIL: 'bg-node-email/15 text-node-email border border-node-email/20',
  IP_ADDRESS: 'bg-node-ip/15 text-node-ip border border-node-ip/20',
  UPI_ID: 'bg-node-upi/15 text-node-upi border border-node-upi/20',
  VEHICLE: 'bg-node-vehicle/15 text-node-vehicle border border-node-vehicle/20',
  DEVICE: 'bg-node-device/15 text-node-device border border-node-device/20',
  LOCATION: 'bg-node-location/15 text-node-location border border-node-location/20',
  ORGANIZATION: 'bg-node-org/15 text-node-org border border-node-org/20',
  BANK_ACCOUNT: 'bg-node-bank/15 text-node-bank border border-node-bank/20',
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
    <div className="space-y-5">
      <div className="flex items-baseline justify-between border-b border-mist-dark pb-3">
        <h1 className="text-lg font-bold text-ink font-mono tracking-wide">ENTITIES</h1>
        <Network className="h-4 w-4 text-gray-400" />
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[180px]">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search entities..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
            className="input-field pl-8 text-xs"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
          className="input-field w-auto text-xs"
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
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card h-20 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
          {data?.items.map((entity) => (
            <div key={entity.id} className="card">
              <div className="flex items-start justify-between">
                <div>
                  <span className={`badge text-[10px] ${entityTypeColors[entity.entity_type] || 'bg-gray-100 text-gray-600 border border-mist-dark'}`}>
                    {entity.entity_type}
                  </span>
                  <p className="mt-1.5 text-sm font-semibold text-ink">{entity.display_value}</p>
                </div>
                <div className="text-right text-[10px] text-gray-400 font-mono">
                  {(entity.confidence * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          ))}
          {data?.items.length === 0 && (
            <div className="col-span-full card text-center py-12">
              <p className="text-xs text-gray-400 font-mono">No entities found.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
