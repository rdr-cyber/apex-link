import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { searchApi } from '@/api'
import { Search as SearchIcon, FolderOpen, Network, FileText } from 'lucide-react'

/* Badge/icon text uses dark-AA variants (ledger in index.css .page-dark). */
const typeIcon = (type: string) => {
  switch (type) {
    case 'CASE': return <FolderOpen className="h-4 w-4 text-[#8fb3de]" />
    case 'EVIDENCE': return <FileText className="h-4 w-4 text-dossier" />
    default: return <Network className="h-4 w-4 text-[#7fa8d4]" />
  }
}

const typeBadge = (type: string) => {
  const map: Record<string, string> = {
    CASE: 'bg-crosscase/10 text-[#8fb3de] border border-crosscase/25',
    EVIDENCE: 'bg-dossier/10 text-dossier border border-dossier/20',
    ENTITY: 'bg-node-person/10 text-[#7fa8d4] border border-node-person/25',
  }
  return `badge text-[10px] ${map[type] || 'bg-white/[0.06] text-gray-400 border border-white/15'}`
}

export function SearchPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['search', query],
    queryFn: () => searchApi.search(query).then((r) => r.data),
    enabled: query.length >= 2,
  })

  return (
    <div className="space-y-5">
      <div className="border-b border-mist-dark pb-3">
        <h1 className="text-lg font-bold text-ink font-mono tracking-wide">SEARCH</h1>
      </div>

      <div className="relative max-w-2xl">
        <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search cases, entities, evidence..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="input-field pl-10 py-2.5 text-sm"
          autoFocus
        />
      </div>

      {isLoading && query.length >= 2 && (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card h-14 animate-pulse" />
          ))}
        </div>
      )}

      {data && data.results.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] text-gray-400 font-mono">{data.total} result(s)</p>
          {data.results.map((result, i) => (
            <div
              key={i}
              className="card card-interactive"
              onClick={() => {
                if (result.type === 'CASE') navigate(`/cases/${result.id}`)
                else if (result.type === 'EVIDENCE') navigate(`/cases/${result.id}`)
                else navigate(`/entities/${result.id}`)
              }}
            >
              <div className="flex items-center gap-2.5">
                {typeIcon(result.type)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className={typeBadge(result.type)}>{result.type}</span>
                    <span className="text-sm font-semibold text-ink truncate">{result.label}</span>
                  </div>
                  <p className="text-[10px] text-gray-500">{result.subtitle}</p>
                </div>
                <span className="text-[10px] text-gray-400 font-mono shrink-0">{result.detail}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {data && data.results.length === 0 && query.length >= 2 && (
        <div className="card text-center py-12">
          <p className="text-xs text-gray-400 font-mono">No results found for "{query}".</p>
        </div>
      )}

      {query.length < 2 && (
        <div className="card text-center py-12">
          <p className="text-xs text-gray-400 font-mono">Type at least 2 characters to search.</p>
        </div>
      )}
    </div>
  )
}
