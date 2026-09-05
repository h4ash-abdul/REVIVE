ex_content = """import { motion } from 'framer-motion'
import { Card, Badge } from '../components/ui'
import { AlertCircle, Ban, ShieldX } from 'lucide-react'

export default function Exceptions() {
  const exceptions = [
    { title: 'MANDATE REVOKED', status: 'BLOCKED', reason: 'Mandate is no longer valid.', next: 'No retry permitted.', icon: ShieldX, color: 'text-red-600', bg: 'bg-red-50' },
    { title: 'UNKNOWN FAILURE', status: 'DEFERRED', reason: 'Recovery not attempted because the failure could not be safely classified.', next: 'Human investigation required.', icon: AlertCircle, color: 'text-orange-600', bg: 'bg-orange-50' },
    { title: 'BUDGET EXHAUSTED', status: 'HALTED', reason: 'Recovery stopped after retry limit (3/3).', next: 'Close case.', icon: Ban, color: 'text-gray-600', bg: 'bg-gray-100' },
  ]

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-8 max-w-[1000px] w-full">
      <div className="flex flex-col gap-2">
        <h1 className="text-[28px] font-bold text-gray-900 tracking-tight">Exceptions & Edge Cases</h1>
        <p className="text-[14px] text-gray-500 max-w-[700px] leading-relaxed">
          Demonstrating when REVIVE knows NOT to act. Deterministic policy rules ensure safety-first behavior.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
        {exceptions.map((ex, i) => (
          <Card key={i} className="flex flex-col h-full border border-gray-200 shadow-sm hover:shadow-md transition-shadow bg-white">
            <div className={p-5 border-b border-gray-100 flex items-center gap-3}>
              <div className={p-2 rounded-md  }>
                <ex.icon className="w-5 h-5" />
              </div>
              <div className="flex flex-col">
                <h3 className="text-[13px] font-bold text-gray-900 uppercase tracking-wider">{ex.title}</h3>
                <Badge variant="low" className={mt-1 text-[9px] font-bold tracking-wider w-fit  }>{ex.status}</Badge>
              </div>
            </div>
            <div className="p-5 flex flex-col gap-4 flex-1">
              <div>
                <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1">Reason</div>
                <p className="text-[13px] text-gray-700 font-medium leading-relaxed m-0">
                  {ex.reason}
                </p>
              </div>
              <div className="mt-auto pt-4 border-t border-gray-100">
                <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1">Next Action</div>
                <p className="text-[13px] text-gray-900 font-semibold m-0">
                  {ex.next}
                </p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </motion.div>
  )
}
"""

ex_content = ex_content.replace("", "").replace("", "")

with open('frontend/src/pages/Exceptions.tsx', 'w', encoding='utf-8') as f:
    f.write(ex_content)
