import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/AuthProvider'
import { DemoBanner } from '@/components/DemoBanner'
import { LogOut } from 'lucide-react'

const navItems = [
  { to: '/dashboard', label: 'DASHBOARD' },
  { to: '/cases', label: 'CASES' },
  { to: '/intelligence', label: 'INTELLIGENCE' },
  { to: '/entities', label: 'ENTITIES' },
  { to: '/leads', label: 'LEADS' },
  { to: '/search', label: 'SEARCH' },
  { to: '/audit', label: 'AUDIT' },
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

/* Routes that render as the dark "analyst console" surface. Exact matches
   only — /cases/new, /cases/:id and /leads/:id keep the cream document
   layout on purpose (forms and long-form reading read better on paper). */
const DARK_CONSOLE_ROUTES = ['/dashboard', '/cases', '/leads', '/entities', '/search', '/audit']

export function MainLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const isDarkConsole = DARK_CONSOLE_ROUTES.includes(pathname)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-cream">
      {/* ── Top bar: logo left · drawer-label nav centered · user right ── */}
      <header className="shrink-0 bg-charcoal border-b border-charcoal-light">
        <div className="flex h-14 items-center gap-6 pl-4 pr-4 xl:pr-6">
          {/* Logo / wordmark — enlarged mark, gap/wrapping tuned so the
              centered nav keeps clear air (verified at 1440px + 1024px) */}
          <NavLink to="/dashboard" className="flex shrink-0 items-center gap-3">
            <img src="/logo-mark-white.svg" alt="APEX LINK logo" className="h-10 w-10" />
            <div>
              <h1 className="text-sm font-extrabold text-white tracking-wider font-mono leading-none">APEX LINK</h1>
              <p className="mt-0.5 text-[9px] text-gray-500 font-mono uppercase tracking-[0.15em]">Investigation Intelligence</p>
            </div>
          </NavLink>

          {/* Drawer-label nav — centered on wide screens, scrolls below xl */}
          <nav className="no-scrollbar -mb-px flex min-w-0 flex-1 items-stretch justify-start gap-1 overflow-x-auto xl:justify-center">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `nav-link flex items-center whitespace-nowrap border-b-2 px-3 py-4 text-[11px] font-semibold font-mono uppercase tracking-[0.14em] transition-colors duration-150 ${
                    isActive
                      ? 'border-dossier text-dossier'
                      : 'border-transparent text-gray-400 hover:border-charcoal-light hover:text-gray-200'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          {/* User / role */}
          <div className="ml-auto flex shrink-0 items-center gap-2.5">
            <div className="relative flex h-8 w-8 items-center justify-center rounded bg-charcoal-light text-[11px] font-bold font-mono text-dossier border border-charcoal-light">
              {user?.full_name?.charAt(0) || '?'}
              <div className={`absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full ${roleDot[user?.role || 'INVESTIGATOR']} border border-charcoal`} />
            </div>
            <div className="hidden min-w-0 sm:block">
              <p className="truncate text-xs font-semibold text-gray-200 leading-tight">{user?.full_name}</p>
              <span className={`inline-flex items-center rounded-sm px-1 py-0.5 text-[9px] font-bold font-mono uppercase ${roleColors[user?.role || 'INVESTIGATOR']}`}>
                {user?.role}
              </span>
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
      </header>

      {/* Main content — dark console surface on list/dashboard routes,
          cream paper everywhere else */}
      <main className={`min-h-0 flex-1 overflow-y-auto ${isDarkConsole ? '' : 'bg-cream'}`}>
        <div className={isDarkConsole ? 'page-dark min-h-full' : ''}>
          <DemoBanner />
          <div className="mx-auto max-w-[1500px] p-5 page-enter">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  )
}
