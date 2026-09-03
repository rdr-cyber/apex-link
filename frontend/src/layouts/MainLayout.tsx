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
  ADMIN: 'from-red-500 to-pink-600',
  INVESTIGATOR: 'from-blue-500 to-cyan-600',
  ANALYST: 'from-emerald-500 to-teal-600',
}

const roleBg: Record<string, string> = {
  ADMIN: 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400',
  INVESTIGATOR: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
  ANALYST: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400',
}

export function MainLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-gray-200/80 dark:border-gray-800/80 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm">
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-gray-200/80 dark:border-gray-800/80 px-5">
          <div className="logo-spin flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-trace-500 via-indigo-500 to-purple-600 shadow-lg shadow-trace-500/20">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-extrabold text-trace-700 dark:text-trace-400 tracking-tight">TRACE-NET</h1>
            <p className="text-[10px] text-gray-400 font-semibold tracking-wide">INVESTIGATION INTELLIGENCE</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-link flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium ${
                  isActive
                    ? 'sidebar-active bg-gradient-to-r from-trace-50 dark:from-trace-950/50 to-transparent text-trace-700 dark:text-trace-300 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50/80 dark:hover:bg-gray-800/40'
                }`
              }
            >
              <item.icon className="h-[18px] w-[18px]" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-gray-200/80 dark:border-gray-800/80 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${roleColors[user?.role || 'INVESTIGATOR']} text-white text-sm font-bold shadow-lg`}>
                {user?.full_name?.charAt(0) || '?'}
                <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-green-400 border-2 border-white dark:border-gray-900" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-gray-900 dark:text-white">{user?.full_name}</p>
                <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase ${roleBg[user?.role || 'INVESTIGATOR']}`}>
                  {user?.role}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="rounded-xl p-2 text-gray-400 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-500 transition-all duration-200 hover:scale-110 active:scale-95"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-gray-50/50 dark:bg-gray-950">
        <DemoBanner />
        <div className="mx-auto max-w-7xl p-6 page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
