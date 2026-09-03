import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/api'
import { FolderOpen, FileText, Network, Users, AlertTriangle, Activity } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#6366f1', '#f59e0b', '#ef4444', '#10b981', '#8b5cf6', '#ec4899']

export function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => dashboardApi.getStats().then((r) => r.data),
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="skeleton h-8 w-40 rounded-lg" />
          <div className="skeleton h-4 w-56 rounded-lg" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card">
              <div className="flex items-center gap-3.5">
                <div className="skeleton h-12 w-12 rounded-xl" />
                <div className="space-y-2">
                  <div className="skeleton h-3 w-20 rounded-md" />
                  <div className="skeleton h-7 w-12 rounded-md" />
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
        <p className="text-red-600">Failed to load dashboard data. Please try again.</p>
      </div>
    )
  }

  if (!data) return null

  const statCards = [
    { label: 'Total Cases', value: data.total_cases, icon: FolderOpen, color: 'bg-trace-600' },
    { label: 'Active Cases', value: data.active_cases, icon: Activity, color: 'bg-green-600' },
    { label: 'Evidence Items', value: data.total_evidence, icon: FileText, color: 'bg-amber-600' },
    { label: 'Entities', value: data.total_entities, icon: Network, color: 'bg-purple-600' },
    { label: 'Relationships', value: data.total_relationships, icon: Users, color: 'bg-blue-600' },
    { label: 'High-Priority Leads', value: data.high_priority_leads, icon: AlertTriangle, color: 'bg-red-600' },
  ]

  const categoryData = Object.entries(data.cases_by_category).map(([name, value]) => ({ name, value }))
  const statusData = Object.entries(data.cases_by_status).map(([name, value]) => ({ name, value }))
  const entityTypeData = Object.entries(data.entity_type_distribution).map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-gray-500">TRACE-NET Investigation Intelligence</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {statCards.map((stat, i) => (
          <div key={stat.label} className={`stat-card animate-delay-${i + 1}`} style={{ animationDelay: `${i * 0.08}s` }}>
            <div className="flex items-center gap-3.5">
              <div className={`stat-icon flex h-12 w-12 items-center justify-center rounded-xl ${stat.color} text-white shadow-lg shadow-${stat.color.replace('bg-', '')}/20`}>
                <stat.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide">{stat.label}</p>
                <p className="text-2xl font-extrabold tracking-tight text-gray-900 dark:text-white">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Cases by category */}
        <div className="card" style={{ animationDelay: '0.5s' }}>
          <h2 className="mb-4 text-sm font-bold text-gray-400 uppercase tracking-wider">Cases by Category</h2>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={categoryData}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-500">No data available</p>
          )}
        </div>

        {/* Cases by status */}
        <div className="card" style={{ animationDelay: '0.6s' }}>
          <h2 className="mb-4 text-sm font-bold text-gray-400 uppercase tracking-wider">Cases by Status</h2>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {statusData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-500">No data available</p>
          )}
        </div>

        {/* Entity type distribution */}
        <div className="card">
          <h2 className="mb-4 text-sm font-bold text-gray-400 uppercase tracking-wider">Entity Types</h2>
          {entityTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={entityTypeData} layout="vertical">
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
                <Tooltip />
                <Bar dataKey="value" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-500">No data available</p>
          )}
        </div>

        {/* Lead priority distribution */}
        <div className="card">
          <h2 className="mb-4 text-sm font-bold text-gray-400 uppercase tracking-wider">Lead Priorities</h2>
          {Object.entries(data.lead_priority_distribution).filter(([, v]) => v > 0).length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={Object.entries(data.lead_priority_distribution)
                    .filter(([, v]) => v > 0)
                    .map(([name, value]) => ({ name, value }))}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {Object.entries(data.lead_priority_distribution)
                    .filter(([, v]) => v > 0)
                    .map((_, index) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} />
                    ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-500">No leads generated yet</p>
          )}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4">
        <p className="text-xs text-amber-700 dark:text-amber-400">
          <strong>Disclaimer:</strong> TRACE-NET is an investigative decision-support platform. All analytical
          scores, correlations, and patterns are potential leads requiring human verification. They do not
          establish criminal responsibility.
        </p>
      </div>
    </div>
  )
}
