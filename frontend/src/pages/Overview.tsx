import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { DemoCase } from '../types'
import { ChevronRight, ArrowUpRight, Clock, AlertCircle } from 'lucide-react'

export default function Overview() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<DemoCase[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<DemoCase[]>('/cases')
      .then(res => setCases(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const activeCases = cases.filter(c => c.initial_probability > 0)
  const readyCases = activeCases.slice(0, 3) // show first 3

  const getConfStyle = (prob: number) => {
    if (prob > 0.7) return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
    if (prob >= 0.4) return 'text-amber-400 bg-amber-400/10 border-amber-400/20'
    return 'text-rose-400 bg-rose-400/10 border-rose-400/20'
  }
  const getConfLabel = (prob: number) => {
    if (prob > 0.7) return 'HIGH'
    if (prob >= 0.4) return 'MODERATE'
    return 'LOW'
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 w-full max-w-[1400px] mx-auto">
      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-bold text-white tracking-widest uppercase">REVIVE <span className="text-gray-600 font-normal">/ RECOVERY OPERATIONS</span></h1>
        <p className="text-[11px] text-gray-500 font-bold tracking-widest uppercase mb-4">Adaptive AI Revenue Recovery Agent</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div 
          className="p-5 flex flex-col gap-1 cursor-pointer group bg-[#16171a] border border-[#222328] hover:border-gray-500 transition-all rounded"
          onClick={() => navigate('/queue?filter=at-risk')}
        >
          <div className="flex justify-between items-center mb-2">
            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Revenue at Risk</div>
            <ArrowUpRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-300 transition-colors" />
          </div>
          <div className="text-[24px] font-mono font-bold text-white tracking-tight">₹128,368<span className="text-[14px] text-gray-600 font-normal">.32</span></div>
          <div className="text-[10px] text-gray-400 flex items-center gap-1 mt-2 uppercase tracking-wider font-bold">
            <AlertCircle className="w-3 h-3 text-rose-500" /> Action Required
          </div>
        </div>
        
        <div 
          className="p-5 flex flex-col gap-1 cursor-pointer group bg-[#16171a] border border-[#222328] hover:border-gray-500 transition-all rounded"
          onClick={() => navigate('/queue?filter=recovered')}
        >
          <div className="flex justify-between items-center mb-2">
            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Recovered</div>
            <ArrowUpRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-300 transition-colors" />
          </div>
          <div className="text-[24px] font-mono font-bold text-emerald-400 tracking-tight">₹50,192<span className="text-[14px] text-emerald-400/50 font-normal">.12</span></div>
          <div className="text-[10px] text-emerald-500 flex items-center gap-1 mt-2 uppercase tracking-wider font-bold">
            +16.43% vs heuristics
          </div>
        </div>
        
        <div 
          className="p-5 flex flex-col gap-1 cursor-pointer group bg-[#16171a] border border-[#222328] hover:border-gray-500 transition-all rounded"
          onClick={() => navigate('/evidence')}
        >
          <div className="flex justify-between items-center mb-2">
            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Recovery Rate</div>
            <ArrowUpRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-300 transition-colors" />
          </div>
          <div className="text-[24px] font-mono font-bold text-white tracking-tight">39.3<span className="text-[14px] text-gray-600 font-normal">%</span></div>
          <div className="text-[10px] text-gray-400 flex items-center gap-1 mt-2 uppercase tracking-wider font-bold">
            Last 60 days
          </div>
        </div>
        
        <div 
          className="p-5 flex flex-col gap-1 cursor-pointer group bg-[#16171a] border border-[#222328] hover:border-gray-500 transition-all rounded"
          onClick={() => navigate('/queue')}
        >
          <div className="flex justify-between items-center mb-2">
            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Actionable Cases</div>
            <ArrowUpRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-300 transition-colors" />
          </div>
          <div className="text-[24px] font-mono font-bold text-white tracking-tight">417</div>
          <div className="text-[10px] text-gray-400 flex items-center gap-1 mt-2 uppercase tracking-wider font-bold">
            <Clock className="w-3 h-3" /> Pending Execution
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4 mt-4">
        <div className="flex items-center justify-between border-b border-[#222328] pb-2">
          <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">READY FOR RECOVERY</h2>
          <span className="text-[10px] text-gray-500 font-bold tracking-widest uppercase cursor-pointer hover:text-white transition-colors" onClick={() => navigate('/queue')}>VIEW ALL {activeCases.length} </span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pb-4">
          {loading ? (
            <div className="text-[12px] text-gray-600 font-mono col-span-3 py-10">LOADING_ACTIVE_CASES...</div>
          ) : readyCases.map(c => (
            <div key={c.scenario_key} className="flex flex-col bg-[#16171a] border border-[#222328] rounded cursor-pointer hover:border-gray-500 transition-all" onClick={() => navigate(`/queue/${c.scenario_key}`)}>
              <div className="p-4 flex flex-col gap-4">
                <div className="flex justify-between items-start">
                  <div className="font-mono font-bold text-[13px] text-gray-300">{c.title}</div>
                  <div className="font-mono font-bold text-[13px] text-white">₹{c.amount.toLocaleString(undefined, {minimumFractionDigits: 0})}</div>
                </div>
                
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Failure</span>
                    <span className="font-mono text-[9px] uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/20 px-1.5 py-0.5 rounded">{c.failure_code}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Confidence</span>
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[9px] font-bold tracking-widest uppercase px-1.5 py-0.5 rounded border ${getConfStyle(c.initial_probability)}`}>
                        {getConfLabel(c.initial_probability)}
                      </span>
                      <span className="font-mono text-[11px] font-bold text-white">{(c.initial_probability * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="mt-auto p-3 border-t border-[#222328] bg-[#1a1b1f] flex justify-between items-center group-hover:bg-[#1e1f24] transition-colors rounded-b">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">INVESTIGATE</span>
                <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
