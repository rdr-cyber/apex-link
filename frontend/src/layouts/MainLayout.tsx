import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/AuthProvider'
import { DemoBanner } from '@/components/DemoBanner'
import {
  LayoutDashboard,
  FolderOpen,
  Network,
  AlertTriangle,
  Search,
  ScrollText,
  LogOut,
  Shield,
  Route,
} from 'lucide-react'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/cases', icon: FolderOpen, label: 'Cases' },
  { to: '/intelligence', icon: Route, label: 'Intelligence' },
  { to: '/entities', icon: Network, label: 'Entities' },
  { to: '/leads', icon: AlertTriangle, label: 'Leads' },
  { to: '/search', icon: Search, label: 'Search' },
  { to: '/audit', icon: ScrollText, label: 'Audit Log' },
]

const roleColors: Record<string, string> = {
  ADMIN: 'bg-alert/20 text-alert',
  INVESTIGATOR: 'bg-crosscase/20 text-crosscase',
  ANALYST: 'bg-field/20 text-field',
}

const roleDot: Record<string, string> = {
  ADMIN: 'bg-alert',
  INVESTIGATOR: 'bg-crosscase',
  ANALYST: 'bg-field',
}

export function MainLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-cream">
      {/* Sidebar — dark investigation workspace */}
      <aside className="flex w-60 flex-col bg-charcoal border-r border-charcoal-light">
        {/* Logo */}
        <div className="flex h-14 items-center gap-2.5 border-b border-charcoal-light px-4">
          <div className="logo-mark">
            <Shield className="h-4.5 w-4.5" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold text-white tracking-wider font-mono">TRACE-NET</h1>
            <p className="text-[9px] text-gray-500 font-mono uppercase tracking-[0.15em]">Intelligence Platform</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 p-2 mt-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-link flex items-center gap-2.5 rounded px-3 py-2 text-[13px] font-medium ${
                  isActive
                    ? 'sidebar-active text-dossier'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-charcoal-light'
                }`
              }
            >
              <item.icon className="h-4 w-4 opacity-70" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-charcoal-light p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="relative flex h-8 w-8 items-center justify-center rounded bg-charcoal-light text-[11px] font-bold font-mono text-dossier border border-charcoal-light">
                {user?.full_name?.charAt(0) || '?'}
                <div className={`absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full ${roleDot[user?.role || 'INVESTIGATOR']} border border-charcoal`} />
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-gray-200">{user?.full_name}</p>
                <span className={`inline-flex items-center rounded-sm px-1 py-0.5 text-[9px] font-bold font-mono uppercase ${roleColors[user?.role || 'INVESTIGATOR']}`}>
                  {user?.role}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="rounded p-1.5 text-gray-500 hover:bg-alert/10 hover:text-alert transition-colors duration-150"
              title="Logout"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content — cream paper surface */}
      <main className="flex-1 overflow-y-auto bg-cream">
        <DemoBanner />
        <div className="mx-auto max-w-7xl p-5 page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
