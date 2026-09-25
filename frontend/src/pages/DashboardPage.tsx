import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/api'
import { FolderOpen, FileText, Network, Users, AlertTriangle, Activity } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { useCountUp } from '@/hooks/useCountUp'

const CHART_COLORS = ['#d4a853', '#2c6fbb', '#c0392b', '#27ae60', '#8b6db5', '#bf6b8a']

// Status-language mapping for the dark dashboard band:
//   gold (glow-neutral) = neutral/positive metrics — the dossier identity
//   blue (glow-info)    = informational/active — Active cases, Evidence
//   red (glow-critical) = alert — HIGH-priority Leads
function StatCard({ stat, index }: { stat: { label: string; value: number; icon: any; accent: string; glow: string }; index: number }) {
  const displayValue = useCountUp(stat.value, 600 + index * 80)
  return (
    <div className={`stat-card ${stat.glow}`} style={{ animationDelay: `${index * 0.05}s` }}>
      <div className="flex items-center gap-2.5">
        <div className="stat-icon flex h-9 w-9 items-center justify-center rounded">
          <stat.icon className={`h-4 w-4 ${stat.accent}`} />
        </div>
        <div>
          <p className="text-label text-gray-400">{stat.label}</p>
          <p className="stat-value font-mono text-2xl font-extrabold tracking-tight leading-none mt-0.5">
            {displayValue}
          </p>
        </div>
      </div>
    </div>
  )
}

export function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => dashboardApi.getStats().then((r) => r.data),
  })

  if (isLoading) {
    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div className="skeleton h-6 w-36 rounded" />
          <div className="skeleton h-3 w-48 rounded" />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card">
              <div className="flex items-center gap-3">
                <div className="skeleton h-10 w-10 rounded" />
                <div className="space-y-1.5">
                  <div className="skeleton h-2.5 w-16 rounded" />
                  <div className="skeleton h-6 w-10 rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <p className="text-sm text-alert">Failed to load dashboard data. Please try again.</p>
      </div>
    )
  }

  if (!data) return null

  const statCards = [
    { label: 'Cases', value: data.total_cases, icon: FolderOpen, accent: 'text-dossier', glow: 'glow-neutral' },
    { label: 'Active', value: data.active_cases, icon: Activity, accent: 'text-field', glow: 'glow-info' },
    { label: 'Evidence', value: data.total_evidence, icon: FileText, accent: 'text-crosscase', glow: 'glow-info' },
    { label: 'Entities', value: data.total_entities, icon: Network, accent: 'text-dossier', glow: 'glow-neutral' },
    { label: 'Links', value: data.total_relationships, icon: Users, accent: 'text-crosscase', glow: 'glow-neutral' },
    { label: 'Leads', value: data.high_priority_leads, icon: AlertTriangle, accent: 'text-alert', glow: 'glow-critical' },
  ]

  const categoryData = Object.entries(data.cases_by_category).map(([name, value]) => ({ name, value }))
  const statusData = Object.entries(data.cases_by_status).map(([name, value]) => ({ name, value }))
  const entityTypeData = Object.entries(data.entity_type_distribution).map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-5">
      <div className="flex items-baseline justify-between border-b border-mist-dark pb-3">
        <h1 className="text-lg font-bold text-ink font-mono tracking-wide">DASHBOARD</h1>
        <p className="text-[10px] text-gray-400 font-mono uppercase tracking-widest">APEX LINK Intelligence</p>
      </div>

      {/* Stat cards — monospace numbers with count-up; dark status band:
          black panel where glow = urgency (gold neutral, blue info, red critical) */}
      <div className="dashboard-dark grid grid-cols-1 gap-3 rounded-lg p-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {statCards.map((stat, i) => (
          <StatCard key={stat.label} stat={stat} index={i} />
        ))}
      </div>

      {/* Charts — clean, no decorative effects */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="section-header">Cases by Category</h2>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={categoryData}>
                <XAxis dataKey="name" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} stroke="#aaa" />
                <YAxis tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} stroke="#aaa" />
                <Tooltip
                  contentStyle={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', border: '1px solid #e8e6e1', borderRadius: 4, background: '#fff' }}
                />
                <Bar dataKey="value" fill="#d4a853" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">No data available</p>
          )}
        </div>

        <div className="card">
          <h2 className="section-header">Cases by Status</h2>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                  labelLine={false}
                >
                  {statusData.map((_, index) => (
                    <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', border: '1px solid #e8e6e1', borderRadius: 4, background: '#fff' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">No data available</p>
          )}
        </div>

        <div className="card">
          <h2 className="section-header">Entity Types</h2>
          {entityTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={entityTypeData} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} stroke="#aaa" />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} width={90} stroke="#aaa" />
                <Tooltip
                  contentStyle={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', border: '1px solid #e8e6e1', borderRadius: 4, background: '#fff' }}
                />
                <Bar dataKey="value" fill="#2c6fbb" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">No data available</p>
          )}
        </div>

        <div className="card">
          <h2 className="section-header">Lead Priorities</h2>
          {Object.entries(data.lead_priority_distribution).filter(([, v]) => v > 0).length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={Object.entries(data.lead_priority_distribution)
                    .filter(([, v]) => v > 0)
                    .map(([name, value]) => ({ name, value }))}
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                  labelLine={false}
                >
                  {Object.entries(data.lead_priority_distribution)
                    .filter(([, v]) => v > 0)
                    .map((_, index) => (
                      <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                </Pie>
                <Tooltip
                  contentStyle={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', border: '1px solid #e8e6e1', borderRadius: 4, background: '#fff' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">No leads generated yet</p>
          )}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="rounded border border-dossier/20 bg-dossier/5 p-3">
        <p className="text-xs text-dossier-dim font-mono">
          <strong className="text-dossier">DISCLAIMER:</strong> All analytical scores, correlations, and patterns are
          potential leads requiring human verification. They do not establish criminal responsibility.
        </p>
      </div>
    </div>
  )
}
