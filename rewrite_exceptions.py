import re
with open('frontend/src/pages/Exceptions.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

new_content = """import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, ShieldX } from 'lucide-react'
import api from '../api/client'
import { TraceData } from '../types'
import { format } from 'date-fns'

export default function Exceptions() {
  const [trace, setTrace] = useState<TraceData | null>(null)
  
  useEffect(() => {
    const init = async () => {
      try {
        let res = await api.get<TraceData>('/cases/E/trace')
        if (!res.data.audit_trail || res.data.audit_trail.length === 0) {
          try {
            await api.post('/cases/E/trigger')
          } catch (e) {
            // expected 400 error due to budget exhaustion
          }
          res = await api.get<TraceData>('/cases/E/trace')
        }
        setTrace(res.data)
      } catch (e) {
        console.error(e)
      }
    }
    init()
  }, [])

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[1400px] w-full mx-auto pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-bold text-white tracking-widest uppercase">POLICY & EXCEPTIONS</h1>
        <p className="text-[11px] text-gray-500 font-bold tracking-widest uppercase mb-4">
          Real-time Audit Trail (Live Policy Precheck Rejection Example - Case E)
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-4">
        {trace?.audit_trail?.map((event, i) => {
          const isRejection = event.event_type === 'POLICY_PRECHECK' && event.details.valid_count === 0
          
          return (
            <div key={i} className="flex flex-col h-full bg-[#16171a] border border-[#222328] rounded overflow-hidden">
              <div className="p-5 border-b border-[#222328] flex items-center gap-4 bg-[#1e1f24]/30">
                <div className={p-2 rounded border }>
                  {isRejection ? <ShieldX className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                </div>
                <div className="flex flex-col gap-1.5">
                  <h3 className="text-[11px] font-bold text-white uppercase tracking-widest leading-none">{event.event_type.replace(/_/g, ' ')}</h3>
                  <span className={	ext-[9px] font-bold tracking-widest uppercase px-1.5 py-0.5 rounded border w-fit leading-none }>
                    {event.actor}
                  </span>
                </div>
              </div>
              <div className="p-5 flex flex-col gap-5 flex-1">
                <div>
                  <div className="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">TIMESTAMP</div>
                  <p className="text-[11px] font-mono text-gray-300 leading-relaxed uppercase m-0">
                    {format(new Date(event.timestamp), 'MMM d, HH:mm:ss.SSS')}
                  </p>
                </div>
                <div className="mt-auto pt-4 border-t border-[#222328]">
                  <div className="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">PAYLOAD</div>
                  <pre className="text-[10px] font-mono font-bold text-white uppercase m-0 whitespace-pre-wrap">
                    {JSON.stringify(event.details, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}
"""

with open('frontend/src/pages/Exceptions.tsx', 'w', encoding='utf-8') as f:
    f.write(new_content)
