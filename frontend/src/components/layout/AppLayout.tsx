import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Inbox, FileText, ShieldAlert, Network } from 'lucide-react'

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()

  const NavItem = ({ to, icon: Icon, label }: any) => {
    const active = location.pathname === to || (to === '/queue' && location.pathname.startsWith('/queue'))
    return (
      <div 
        onClick={() => navigate(to)}
        className={`flex flex-col items-center gap-1.5 p-3 rounded-lg cursor-pointer transition-colors ${
          active ? 'bg-[#222328] text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-[#1a1b1f]'
        }`}
      >
        <Icon className="w-5 h-5" />
        <span className="text-[9px] font-bold tracking-widest uppercase">{label}</span>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-[#0a0a0b] text-gray-100 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <div className="w-[88px] bg-[#121316] border-r border-[#222328] flex flex-col items-center py-6 shrink-0 z-50">
        <div className="w-10 h-10 bg-white rounded flex items-center justify-center mb-8 cursor-pointer" onClick={() => navigate('/')}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#121316" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
        </div>
        
        <div className="flex flex-col gap-4 w-full px-3">
          <NavItem to="/" icon={LayoutDashboard} label="Overview" />
          <NavItem to="/queue" icon={Inbox} label="Queue" />
          <NavItem to="/architecture" icon={Network} label="System" />
          <NavItem to="/evidence" icon={FileText} label="Evidence" />
          <NavItem to="/exceptions" icon={ShieldAlert} label="Policy" />
        </div>

        <div className="mt-auto flex flex-col items-center gap-4 w-full">
          <div className="flex flex-col items-center gap-1.5 opacity-60">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[8px] font-bold tracking-widest text-emerald-500 uppercase">SYS_OK</span>
          </div>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* TOP BAR */}
        <div className="h-12 border-b border-[#222328] bg-[#121316]/50 flex items-center justify-between px-6 shrink-0 z-40 backdrop-blur-md">
          <div className="text-[10px] font-mono text-gray-500 tracking-widest uppercase">REVIVE_CORE // V2.1.4</div>
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#1e1f24] border border-[#2a2b30]">
            <ShieldAlert className="w-3 h-3 text-emerald-400" />
            <span className="text-[9px] font-bold tracking-widest text-emerald-400 uppercase">SECURE · SIMULATED DATA</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 md:p-8">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
