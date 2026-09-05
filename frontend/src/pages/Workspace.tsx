import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Search, ChevronRight } from 'lucide-react'
import api from '../api/client'
import { DemoCase } from '../types'
import { Badge } from '../components/ui'
import CaseDetail from './CaseDetail'

export default function Workspace() {
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const filterParams = searchParams.get('filter') || 'all'
  
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

  const filtered = cases.filter(c => {
    const matchSearch = c.title.toLowerCase().includes(search.toLowerCase()) || c.failure_code.toLowerCase().includes(search.toLowerCase());
    if (filterParams === 'active') return matchSearch && c.initial_probability > 0;
    if (filterParams === 'recovered') return false; 
    return matchSearch;
  });

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-80px)] overflow-hidden gap-6 -m-2 p-2">
      <motion.div 
        initial={{ opacity: 0, x: -20 }} 
        animate={{ opacity: 1, x: 0 }} 
        className={`w-full lg:w-1/3 lg:min-w-[350px] lg:max-w-[400px] flex flex-col gap-4 overflow-y-auto pr-2 ${id ? 'hidden lg:flex' : 'flex'}`}
      >
        <div className="flex items-center gap-2 px-3 py-2 bg-panel border border-borderRef rounded-[3px] sticky top-0 z-10 shadow-sm">
          <Search className="w-3.5 h-3.5 text-textTertiary" />
          <input 
            type="text" 
            placeholder="Search queue..." 
            className="border-none outline-none bg-transparent text-[12px] text-textPrimary w-full placeholder:text-textTertiary"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2">
          {loading ? (
            <div className="p-5 text-center text-textSecondary text-[12px]">Loading queue...</div>
          ) : (
            filtered.map((c) => {
              const isSelected = c.scenario_key === id;
              return (
                <div 
                  key={c.scenario_key}
                  onClick={() => navigate(`/queue/${c.scenario_key}`)}
                  className={`relative group p-4 rounded-[3px] cursor-pointer transition-all ${isSelected ? 'bg-panel border border-accent ring-1 ring-accent shadow-sm' : 'bg-panel border border-borderRef hover:border-borderStrong hover:shadow-sm'}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="font-semibold text-textPrimary text-[13px]">{c.title}</div>
                    <div className="font-semibold text-textPrimary text-[13px]">₹{c.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                  </div>
                  
                  <div className="flex items-center gap-2 mb-3">
                    <Badge variant="critical">{c.failure_code}</Badge>
                    <Badge variant="low">READY</Badge>
                  </div>
                  
                  <div className="flex items-center justify-between mt-2 pt-3 border-t border-borderRef">
                    <div className="flex items-center gap-1.5 text-[11px] font-medium text-textSecondary">
                      Prediction <span className={c.initial_probability > 0 ? "text-elevated font-semibold" : ""}>{c.initial_probability > 0 ? (c.initial_probability * 100).toFixed(0) + '%' : 'N/A'}</span>
                    </div>
                    
                    <div className={`text-[10px] font-semibold tracking-wider uppercase flex items-center transition-opacity ${isSelected ? 'text-accent opacity-100' : 'text-textTertiary opacity-100 lg:opacity-0 group-hover:opacity-100'}`}>
                      {isSelected ? 'INSPECTING' : 'VIEW CASE'} <ChevronRight className="w-3 h-3 ml-0.5" />
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </motion.div>

      <div className={`w-full lg:w-2/3 flex-col bg-page lg:border-l border-borderRef lg:pl-6 overflow-y-auto ${!id ? 'hidden lg:flex' : 'flex'}`}>
        <AnimatePresence mode="wait">
          {id ? (
            <motion.div key={id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="h-full flex justify-center">
              <CaseDetail />
            </motion.div>
          ) : (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center h-full text-textTertiary gap-4">
              <div className="w-16 h-16 rounded-full bg-panel border border-borderRef flex items-center justify-center shadow-sm">
                <Search className="w-6 h-6" />
              </div>
              <div className="text-[13px] font-medium">Select a case from the queue to investigate</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
