import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { searchApi } from '@/api'
import { Search as SearchIcon, FolderOpen, Network, FileText } from 'lucide-react'

const typeIcon = (type: string) => {
  switch (type) {
    case 'CASE': return <FolderOpen className="h-5 w-5 text-blue-500" />
    case 'EVIDENCE': return <FileText className="h-5 w-5 text-amber-500" />
    default: return <Network className="h-5 w-5 text-purple-500" />
  }
}

const typeColor = (type: string) => {
  switch (type) {
    case 'CASE': return 'bg-blue-100 text-blue-800'
    case 'EVIDENCE': return 'bg-amber-100 text-amber-800'
    default: return 'bg-purple-100 text-purple-800'
  }
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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Search</h1>

      <div className="relative max-w-2xl">
        <SearchIcon className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search cases, entities, evidence..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="input-field pl-12 py-3 text-lg"
          autoFocus
        />
      </div>

      {isLoading && query.length >= 2 && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card animate-pulse h-16" />
          ))}
        </div>
      )}

      {data && data.results.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-gray-500">{data.total} result(s) found</p>
          {data.results.map((result, i) => (
            <div
              key={i}
              className="card cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              onClick={() => {
                if (result.type === 'CASE') navigate(`/cases/${result.id}`)
                else if (result.type === 'EVIDENCE') navigate(`/cases/${result.id}`)
                else navigate(`/entities/${result.id}`)
              }}
            >
              <div className="flex items-center gap-3">
                {typeIcon(result.type)}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`badge text-xs ${typeColor(result.type)}`}>{result.type}</span>
                    <span className="font-medium">{result.label}</span>
                  </div>
                  <p className="text-sm text-gray-500">{result.subtitle}</p>
                </div>
                <span className="text-xs text-gray-400">{result.detail}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {data && data.results.length === 0 && query.length >= 2 && (
        <div className="card text-center py-12">
          <p className="text-sm text-gray-500">No results found for "{query}".</p>
        </div>
      )}

      {query.length < 2 && (
        <div className="card text-center py-12">
          <p className="text-sm text-gray-500">Type at least 2 characters to search.</p>
        </div>
      )}
    </div>
  )
}
