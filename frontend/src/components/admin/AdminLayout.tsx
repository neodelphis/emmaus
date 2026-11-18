import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  CalendarDays,
  Clock3,
  LogOut,
  UserCog,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { useAuth } from '../../auth'
import { cn } from '../../lib/cn'
import { Logo } from '../ui/Logo'

interface NavItem {
  to: string
  label: string
  shortLabel: string
  icon: LucideIcon
}

const navItems: NavItem[] = [
  { to: '/admin/semaine', label: 'Planning de la semaine', shortLabel: 'Planning', icon: CalendarDays },
  { to: '/admin/benevoles', label: 'Bénévoles', shortLabel: 'Bénévoles', icon: Users },
  { to: '/admin/horaires', label: 'Horaires', shortLabel: 'Horaires', icon: Clock3 },
  { to: '/admin/compte', label: 'Compte', shortLabel: 'Compte', icon: UserCog },
]

function DesktopNavItem({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition',
          isActive
            ? 'bg-white/10 text-white ring-1 ring-white/10'
            : 'text-brand-100/80 hover:bg-white/5 hover:text-white',
        )
      }
    >
      <Icon className="h-[18px] w-[18px]" aria-hidden />
      {item.label}
    </NavLink>
  )
}

function MobileNavItem({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        cn(
          'flex flex-1 flex-col items-center gap-1 rounded-lg px-1 py-2 text-[11px] font-medium transition',
          isActive ? 'text-brand-700' : 'text-stone-500',
        )
      }
    >
      {({ isActive }) => (
        <>
          <span
            className={cn(
              'flex h-8 w-12 items-center justify-center rounded-lg transition',
              isActive && 'bg-brand-50',
            )}
          >
            <Icon className="h-5 w-5" aria-hidden />
          </span>
          {item.shortLabel}
        </>
      )}
    </NavLink>
  )
}

export function AdminLayout() {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const activeItem = navItems.find((item) => location.pathname.startsWith(item.to))

  return (
    <div className="min-h-screen bg-stone-100">
      <a
        href="#contenu-admin"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:shadow"
      >
        Aller au contenu
      </a>

      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-brand-950 px-4 py-6 md:flex">
        <div className="px-2">
          <Logo />
        </div>
        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {navItems.map((item) => (
            <DesktopNavItem key={item.to} item={item} />
          ))}
        </nav>
        <div className="mt-6 rounded-xl bg-white/5 p-3 ring-1 ring-white/10">
          <p className="truncate text-xs text-brand-100/70">Connecté·e</p>
          <p className="mt-0.5 truncate text-sm font-medium text-white">{user?.email}</p>
          <button
            type="button"
            onClick={() => void signOut()}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-xs font-semibold text-white transition hover:bg-white/15"
          >
            <LogOut className="h-3.5 w-3.5" aria-hidden />
            Se déconnecter
          </button>
        </div>
      </aside>

      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-stone-200 bg-white/95 px-4 py-3 backdrop-blur md:hidden">
        <Logo variant="dark" />
        <div className="flex items-center gap-3">
          <span className="max-w-[9rem] truncate text-xs text-stone-500">{user?.email}</span>
          <button
            type="button"
            onClick={() => void signOut()}
            className="rounded-lg p-2 text-stone-500 transition hover:bg-stone-100 hover:text-stone-800"
            aria-label="Se déconnecter"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </header>

      <main id="contenu-admin" className="pb-24 md:pl-64 md:pb-10">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 md:px-8 md:py-8">
          <p className="mb-1 hidden text-xs font-semibold uppercase tracking-wide text-stone-400 md:block">
            Administration
          </p>
          {activeItem && (
            <p className="mb-4 text-xs font-semibold uppercase tracking-wide text-stone-400 md:hidden">
              {activeItem.label}
            </p>
          )}
          <Outlet />
        </div>
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-30 flex items-stretch border-t border-stone-200 bg-white/95 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden">
        {navItems.map((item) => (
          <MobileNavItem key={item.to} item={item} />
        ))}
      </nav>
    </div>
  )
}
