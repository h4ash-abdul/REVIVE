import os

app_layout = '''import { NavLink, Outlet } from 'react-router-dom'
import { Activity, LayoutDashboard, ListTodo, ShieldAlert, FileSearch, Network } from 'lucide-react'
import { cn } from '../../lib/utils'

const NAV_ITEMS = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/queue', label: 'Recovery Queue', icon: ListTodo },
  { path: '/exceptions', label: 'Exceptions', icon: ShieldAlert },
  { path: '/evidence', label: 'Evidence', icon: FileSearch },
  { path: '/architecture', label: 'Architecture', icon: Network },
]

export function AppLayout() {
  return (
    <div className="flex min-h-screen w-full bg-[#f4f5f7] text-[#1f2023] font-sans">
      <aside className="w-[220px] flex-shrink-0 bg-[#121316] flex flex-col py-6">
        <div className="px-6 pb-6 text-white text-[13px] font-bold tracking-[1.5px] flex items-center gap-2">
          <div className="w-4 h-4 rounded-sm bg-accent flex items-center justify-center" />
          REVIVE
        </div>
        <div className="h-[1px] bg-[#222328] mb-4" />
        
        <nav className="flex flex-col gap-1 px-3">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    "px-3 py-2 text-[12px] font-medium tracking-[0.2px] transition-all rounded-[4px] flex items-center gap-2.5",
                    isActive
                      ? "bg-[#222328] text-white"
                      : "text-[#8b8d98] hover:text-[#c4c5ce] hover:bg-[#1a1b1f]"
                  )
                }
              >
                <Icon className="w-3.5 h-3.5" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>
        
        <div className="mt-auto px-6 pt-4">
          <div className="h-[1px] bg-[#222328] mb-4 -mx-6" />
          <div className="flex items-center justify-between text-[#8b8d98] text-[11px] font-semibold tracking-wider uppercase">
            SYSTEM
            <span className="flex items-center gap-1.5 text-[#34d399]">
              <div className="w-1.5 h-1.5 rounded-full bg-[#34d399] animate-pulse" />
              Operational
            </span>
          </div>
        </div>
      </aside>
      
      <main className="flex-1 min-w-0 p-8 lg:p-12 flex flex-col gap-5 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
'''
with open('frontend/src/components/layout/AppLayout.tsx', 'w', encoding='utf-8') as f:
    f.write(app_layout)
