import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/api'
import { FolderOpen, FileText, Network, Users, AlertTriangle, Activity } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { useCountUp } from '@/hooks/useCountUp'

const CHART_COLORS = ['#d4a853', '#2c6fbb', '#c0392b', '#27ae60', '#8b6db5', '#bf6b8a']

/* Dark-surface chart chrome (see WCAG ledger in index.css .page-dark):
   axis/tick text ≥ 7:1, gridlines/axis lines pass the 1.4.11 3:1 non-text bar.
   Series colors are unchanged — mid-luminance tones hold ≥ 3:1 on the dark
   panel, and gold stays the first pie color to keep the identity. */
const DARK_AXIS_LINE = '#5b6472'
const DARK_TICK = { fontSize: 10, fontFamily: 'JetBrains Mono, monospace', fill: '#9ca3af' }
const DARK_TOOLTIP = {
  fontSize: 11,
  fontFamily: 'JetBrains Mono, monospace',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 4,
  background: 'rgba(20, 23, 31, 0.95)',
  color: '#f9fafb',
}

/* Pie labels: neutral gray-300 (#d1d5db ≈ 11.9:1 on the dark panel) instead of
   series colors — red/blue/green label text fell below 4.5:1 on dark (and
   green-on-cream was already non-AA before the dark mode). The slices keep
   the semantic colors; only the caption text is neutralized. */
const RADIAN = Math.PI / 180
const pieLabel = (props: any) => {
  const { cx, cy, midAngle, outerRadius, name, value } = props
  const sin = Math.sin(midAngle * RADIAN)
  const cos = Math.cos(midAngle * RADIAN)
  const x = cx + (outerRadius + 10) * cos
  const y = cy + (outerRadius + 10) * sin
  return (
    <text
      x={x}
      y={y}
      fill="#d1d5db"
      fontSize={11}
      fontFamily="JetBrains Mono, monospace"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
    >
      {`${name}: ${value}`}
    </text>
  )
}

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
          <p className="stat-value font-mono text-2xl font-extrabold tracking-tight leading-none mt-0.5 text-gray-50">
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
        <p className="text-sm text-[#e87465]">Failed to load dashboard data. Please try again.</p>
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
  // Zero-count statuses would render degenerate slices with overlapping
  // "X: 0" labels — filter them, same rule the lead-priorities pie applies.
  const statusData = Object.entries(data.cases_by_status)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }))
  const entityTypeData = Object.entries(data.entity_type_distribution).map(([name, value]) => ({ name, value }))

  return (      <div className="space-y-5">
      <div className="flex items-baseline justify-between border-b border-white/10 pb-3">
        <h1 className="text-lg font-bold text-gray-50 font-mono tracking-wide">DASHBOARD</h1>
        <p className="text-[10px] text-gray-400 font-mono uppercase tracking-widest">APEX LINK Intelligence</p>
      </div>

      {/* Stat cards — monospace numbers with count-up; dark status band:
          black panel where glow = urgency (gold neutral, blue info, red critical) */}
      <div className="dashboard-dark grid grid-cols-1 gap-3 rounded-lg p-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {statCards.map((stat, i) => (
          <StatCard key={stat.label} stat={stat} index={i} />
        ))}
      </div>

      {/* Charts — dark panels, dark-axis chrome, unchanged data semantics */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="section-header">Cases by Category</h2>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={categoryData}>
                <XAxis dataKey="name" tick={DARK_TICK} stroke={DARK_AXIS_LINE} />
                <YAxis tick={DARK_TICK} stroke={DARK_AXIS_LINE} />
                <Tooltip contentStyle={DARK_TOOLTIP} cursor={{ fill: 'rgba(255,255,255,0.06)' }} />
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
                  label={pieLabel}
                  labelLine={false}
                >
                  {statusData.map((_, index) => (
                    <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={DARK_TOOLTIP} />
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
                <XAxis type="number" tick={DARK_TICK} stroke={DARK_AXIS_LINE} />
                <YAxis dataKey="name" type="category" tick={DARK_TICK} width={90} stroke={DARK_AXIS_LINE} />
                <Tooltip contentStyle={DARK_TOOLTIP} cursor={{ fill: 'rgba(255,255,255,0.06)' }} />
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
                  label={pieLabel}
                  labelLine={false}
                >
                  {Object.entries(data.lead_priority_distribution)
                    .filter(([, v]) => v > 0)
                    .map((_, index) => (
                      <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                </Pie>
                <Tooltip contentStyle={DARK_TOOLTIP} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">No leads generated yet</p>
          )}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="rounded border border-dossier/20 bg-white/[0.04] p-3">
        <p className="text-xs text-dossier font-mono">
          <strong className="text-dossier">DISCLAIMER:</strong> All analytical scores, correlations, and patterns are
          potential leads requiring human verification. They do not establish criminal responsibility.
        </p>
      </div>
    </div>
  )
}
