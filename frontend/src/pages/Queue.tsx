import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import api from '../api/client'
import { DemoCase } from '../types'
import { Badge } from '../components/ui'

export default function Queue() {
  const [cases, setCases] = useState<DemoCase[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api.get<DemoCase[]>('/cases')
      .then(res => setCases(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const filtered = cases.filter(c => c.title.toLowerCase().includes(search.toLowerCase()) || c.failure_code.toLowerCase().includes(search.toLowerCase()))

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-[20px]">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 w-[440px] px-3 py-[9px] bg-panel border border-borderRef rounded-[3px]">
          <Search className="w-3.5 h-3.5 text-textTertiary" />
          <input 
            type="text" 
            placeholder="Search failed payments..." 
            className="border-none outline-none bg-transparent text-[12px] text-textPrimary w-full placeholder:text-textTertiary"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex-1" />
        <span className="px-2 py-1 bg-lowBg rounded-[2px] text-[9px] font-semibold tracking-[0.5px] text-textSecondary uppercase">
          Synthetic Data
        </span>
      </div>

      <div>
        <h1 className="text-[22px] font-semibold m-0 text-textPrimary">Recovery Queue</h1>
        <p className="text-[12.5px] text-textSecondary m-0 mt-1">Review and manage failed recurring payments requiring recovery action.</p>
      </div>

      <div className="bg-panel border border-borderRef rounded-[3px] overflow-hidden">
        <div className="grid grid-cols-5 px-5 py-3 bg-panelAlt text-[10px] font-semibold tracking-[0.4px] text-textTertiary uppercase border-b border-borderRef">
          <div>Case Title</div>
          <div>Amount</div>
          <div>Failure Code</div>
          <div>Recovery Probability</div>
          <div>Status</div>
        </div>
        {loading ? (
          <div className="p-5 text-center text-textSecondary text-[12px]">Loading...</div>
        ) : (
          <div className="flex flex-col">
            {filtered.map((c) => (
              <div 
                key={c.scenario_key}
                onClick={() => navigate('/case/' + c.scenario_key)}
                className="grid grid-cols-5 px-5 py-3 text-[12px] cursor-pointer hover:bg-panelAlt border-b border-borderRef last:border-b-0 transition-colors"
              >
                <div className="font-semibold text-textPrimary">{c.title}</div>
                <div className="text-textSecondary">₹{c.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                <div>
                  <Badge variant="critical">{c.failure_code}</Badge>
                </div>
                <div className="text-textSecondary">
                  {c.initial_probability > 0 ? (
                    <span className="text-elevated font-semibold">{(c.initial_probability * 100).toFixed(1)}%</span>
                  ) : (
                    <span>N/A</span>
                  )}
                </div>
                <div>
                  <Badge variant="low">READY</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}
