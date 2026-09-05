import { NavLink, Outlet } from 'react-router-dom'
import { Activity } from 'lucide-react'
import { cn } from '../../lib/utils'

const NAV_ITEMS = [
  { path: '/', label: 'Overview' },
  { path: '/queue', label: 'Recovery Queue' },
  { path: '/exceptions', label: 'Exceptions' },
  { path: '/evidence', label: 'Evidence' },
]

export function AppLayout() {
  return (
    <div className="flex min-h-screen w-full bg-page text-textPrimary text-xs-plus font-sans">
      <aside className="w-[200px] flex-shrink-0 bg-navBg flex flex-col py-5">
        <div className="px-5 pb-[18px] text-white text-sm font-semibold tracking-[1.2px]">
          REVIVE
        </div>
        <div className="h-[1px] bg-[#38383c] mb-3" />
        
        <nav className="flex flex-col gap-[1px]">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "px-4 py-[11px] pl-5 text-[11px] font-medium tracking-[0.2px] transition-colors",
                  isActive
                    ? "bg-navActive text-navTextActive font-semibold"
                    : "text-navText hover:text-[#d5d5d9]"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        
        <div className="mt-auto px-5 pt-4">
          <div className="flex items-center gap-2 text-navText text-[11px] font-medium">
            System Status
            <span className="flex items-center gap-1.5 text-success ml-auto">
              <Activity className="w-3 h-3" />
              Operational
            </span>
          </div>
        </div>
      </aside>
      
      <main className="flex-1 min-w-0 p-7 lg:p-10 flex flex-col gap-5 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
