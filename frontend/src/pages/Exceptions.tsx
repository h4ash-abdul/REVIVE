import { motion } from 'framer-motion'
import { AlertCircle, Ban, ShieldX } from 'lucide-react'

export default function Exceptions() {
  const exceptions = [
    { title: 'MANDATE REVOKED', status: 'BLOCKED', reason: 'Mandate is no longer valid.', next: 'No retry permitted.', icon: ShieldX, color: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/20' },
    { title: 'UNKNOWN FAILURE', status: 'DEFERRED', reason: 'Recovery not attempted because the failure could not be safely classified.', next: 'Human investigation required.', icon: AlertCircle, color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20' },
    { title: 'BUDGET EXHAUSTED', status: 'HALTED', reason: 'Recovery stopped after retry limit (3/3).', next: 'Close case.', icon: Ban, color: 'text-gray-400', bg: 'bg-gray-700/30', border: 'border-gray-600/30' },
  ]

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[1400px] w-full mx-auto pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-bold text-white tracking-widest uppercase">POLICY & EXCEPTIONS</h1>
        <p className="text-[11px] text-gray-500 font-bold tracking-widest uppercase mb-4">
          Deterministic rules guaranteeing safety-first behavior.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
        {exceptions.map((ex, i) => (
          <div key={i} className="flex flex-col h-full bg-[#16171a] border border-[#222328] rounded overflow-hidden">
            <div className="p-5 border-b border-[#222328] flex items-center gap-4 bg-[#1e1f24]/30">
              <div className={`p-2 rounded border ${ex.bg} ${ex.border} ${ex.color}`}>
                <ex.icon className="w-5 h-5" />
              </div>
              <div className="flex flex-col gap-1.5">
                <h3 className="text-[11px] font-bold text-white uppercase tracking-widest leading-none">{ex.title}</h3>
                <span className={`text-[9px] font-bold tracking-widest uppercase px-1.5 py-0.5 rounded border w-fit leading-none ${ex.bg} ${ex.border} ${ex.color}`}>{ex.status}</span>
              </div>
            </div>
            <div className="p-5 flex flex-col gap-5 flex-1">
              <div>
                <div className="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">REASON</div>
                <p className="text-[11px] font-mono text-gray-300 leading-relaxed uppercase m-0">
                  {ex.reason}
                </p>
              </div>
              <div className="mt-auto pt-4 border-t border-[#222328]">
                <div className="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">NEXT ACTION</div>
                <p className="text-[11px] font-mono font-bold text-white uppercase m-0">
                  {ex.next}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
