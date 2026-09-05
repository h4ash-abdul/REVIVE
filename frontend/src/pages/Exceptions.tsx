import { motion } from 'framer-motion'
import { Card } from '../components/ui'
import { AlertCircle, Ban, Clock, ShieldX } from 'lucide-react'

export default function Exceptions() {
  const exceptions = [
    { title: 'MANDATE EXPIRED', reason: 'Recovery blocked.', icon: Clock, desc: 'The underlying e-mandate has passed its expiration date. No further recovery action can be taken without a new mandate.' },
    { title: 'UNKNOWN FAILURE', reason: 'Recovery not attempted.', icon: AlertCircle, desc: 'The network returned an unmapped or fatal failure code. The ML agent correctly deferred to human investigation.' },
    { title: 'BUDGET EXHAUSTED', reason: 'Recovery stopped.', icon: Ban, desc: 'Maximum configured retries (3) have been consumed. The case is halted to avoid payment network penalties.' },
    { title: 'POLICY REJECTED', reason: 'Execution prevented.', icon: ShieldX, desc: 'The deterministic policy engine rejected the AI-proposed candidate due to a minimum-hours-between-retries violation.' },
  ]

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[900px]">
      <div>
        <h1 className="text-[22px] font-semibold m-0 text-textPrimary">Exceptions</h1>
        <p className="text-[12.5px] text-textSecondary m-0 mt-1 max-w-[600px] leading-relaxed">
          Demonstrating when the agent knows NOT to act. Deterministic policy rules and safe-by-default behavior.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {exceptions.map((ex, i) => (
          <Card key={i} className="p-6 flex flex-col gap-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-criticalBg rounded-[3px] text-critical">
                  <ex.icon className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-[13px] font-semibold tracking-[0.2px] text-textPrimary">{ex.title}</h3>
                  <div className="text-[11px] text-critical font-medium">{ex.reason}</div>
                </div>
              </div>
            </div>
            <p className="text-[12px] text-textSecondary leading-relaxed m-0">
              {ex.desc}
            </p>
          </Card>
        ))}
      </div>
    </motion.div>
  )
}
