import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Search, Inbox } from 'lucide-react'
import api from '../api/client'
import { DemoCase } from '../types'
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
    if (filterParams === 'high') return matchSearch && c.initial_probability > 0.7;
    if (filterParams === 'moderate') return matchSearch && c.initial_probability >= 0.4 && c.initial_probability <= 0.7;
    if (filterParams === 'low') return matchSearch && c.initial_probability < 0.4 && c.initial_probability > 0;
    if (filterParams === 'blocked') return matchSearch && c.initial_probability === 0;
    if (filterParams === 'at-risk' || filterParams === 'active') return matchSearch && c.initial_probability > 0;
    return matchSearch;
  });

  const FilterChip = ({ label, value }: { label: string, value: string }) => {
    const active = filterParams === value || (filterParams === 'at-risk' && value === 'active')
    return (
      <div 
        onClick={() => navigate(`/queue?filter=${value}`)}
        className={`px-3 py-1.5 rounded cursor-pointer text-[9px] font-bold tracking-widest uppercase transition-colors border ${
          active ? 'bg-gray-800 text-white border-gray-600' : 'bg-transparent text-gray-500 border-transparent hover:text-gray-300'
        }`}
      >
        {label}
      </div>
    )
  }

  const getConfStyle = (prob: number) => {
    if (prob === 0) return 'text-gray-500 bg-gray-500/10 border-gray-500/20'
    if (prob > 0.7) return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
    if (prob >= 0.4) return 'text-amber-400 bg-amber-400/10 border-amber-400/20'
    return 'text-rose-400 bg-rose-400/10 border-rose-400/20'
  }

  const getConfLabel = (prob: number) => {
    if (prob === 0) return 'BLOCKED'
    if (prob > 0.7) return 'HIGH'
    if (prob >= 0.4) return 'MODERATE'
    return 'LOW'
  }

  return (
    <div className="flex flex-col xl:flex-row h-[calc(100vh-120px)] overflow-hidden gap-4 -m-4 p-4">
      <motion.div 
        initial={{ opacity: 0, x: -20 }} 
        animate={{ opacity: 1, x: 0 }} 
        className={`w-full xl:w-[45%] flex flex-col bg-[#121316] border border-[#222328] rounded shadow-lg overflow-hidden ${id ? 'hidden xl:flex' : 'flex'}`}
      >
        <div className="flex flex-col border-b border-[#222328] bg-[#16171a]">
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[#222328]">
            <Search className="w-4 h-4 text-gray-500" />
            <input 
              type="text" 
              placeholder="SEARCH QUEUE BY CASE OR CODE..." 
              className="border-none outline-none bg-transparent text-[11px] font-mono text-gray-100 w-full placeholder:text-gray-600 tracking-wider"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-1 p-2 overflow-x-auto scrollbar-hide">
            <FilterChip label="ALL" value="all" />
            <div className="w-px h-3 bg-[#222328] mx-1" />
            <FilterChip label="HIGH CONF" value="high" />
            <FilterChip label="MODERATE" value="moderate" />
            <FilterChip label="LOW" value="low" />
            <FilterChip label="BLOCKED" value="blocked" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-[#0a0a0b]">
          {loading ? (
            <div className="p-10 text-center text-gray-600 font-mono text-[11px]">LOADING_DATA...</div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead className="bg-[#121316] text-[9px] uppercase tracking-widest text-gray-500 font-bold sticky top-0 z-10 border-b border-[#222328]">
                <tr>
                  <th className="px-4 py-3 font-bold">MANDATE ID</th>
                  <th className="px-3 py-3 font-bold text-right">AMOUNT</th>
                  <th className="px-3 py-3 font-bold">FAILURE CODE</th>
                  <th className="px-4 py-3 font-bold text-right">CONFIDENCE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e1f24]">
                {filtered.map((c) => {
                  const isSelected = c.scenario_key === id;
                  return (
                    <tr 
                      key={c.scenario_key}
                      onClick={() => navigate(`/queue/${c.scenario_key}`)}
                      className={`group cursor-pointer transition-colors ${isSelected ? 'bg-[#1a1b1f]' : 'hover:bg-[#121316]'}`}
                    >
                      <td className="px-4 py-3 align-top">
                        <div className={`text-[12px] font-mono font-bold ${isSelected ? 'text-white' : 'text-gray-300'}`}>{c.title}</div>
                        <div className="text-[9px] text-gray-500 mt-1 font-bold tracking-widest uppercase">ACTION: TOMORROW 09:00</div>
                      </td>
                      <td className="px-3 py-3 align-top text-right">
                        <div className={`text-[12px] font-mono font-bold ${isSelected ? 'text-white' : 'text-gray-300'}`}>₹{c.amount.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
                      </td>
                      <td className="px-3 py-3 align-top">
                        <div className="text-[10px] font-mono text-gray-400 bg-[#16171a] border border-[#222328] rounded px-1.5 py-0.5 inline-block truncate max-w-[120px]">{c.failure_code}</div>
                      </td>
                      <td className="px-4 py-3 align-top text-right">
                        <div className="flex flex-col items-end gap-1">
                          <span className={`text-[9px] font-bold tracking-widest uppercase px-1.5 py-0.5 rounded border ${getConfStyle(c.initial_probability)}`}>
                            {getConfLabel(c.initial_probability)}
                          </span>
                          {c.initial_probability > 0 && (
                            <span className="text-[11px] font-mono text-gray-400">{(c.initial_probability * 100).toFixed(0)}%</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </motion.div>

      <div className={`w-full xl:w-[55%] flex-col overflow-y-auto ${!id ? 'hidden xl:flex' : 'flex'}`}>
        <AnimatePresence mode="wait">
          {id ? (
            <motion.div key={id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="h-full flex justify-center w-full">
              <CaseDetail />
            </motion.div>
          ) : (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center h-full text-gray-600 gap-4 bg-[#121316] border border-[#222328] shadow-sm rounded m-1">
              <Inbox className="w-8 h-8 text-[#222328]" />
              <div className="text-[10px] font-bold tracking-widest uppercase">SELECT A MANDATE TO INVESTIGATE</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
