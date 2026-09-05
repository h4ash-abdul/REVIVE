import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Search, Inbox } from 'lucide-react'
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
    <div className="flex flex-col xl:flex-row h-[calc(100vh-100px)] overflow-hidden gap-6 -m-4 p-4">
      <motion.div 
        initial={{ opacity: 0, x: -20 }} 
        animate={{ opacity: 1, x: 0 }} 
        className={`w-full xl:w-5/12 flex flex-col bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden ${id ? 'hidden xl:flex' : 'flex'}`}
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 bg-gray-50/50">
          <Search className="w-4 h-4 text-gray-400" />
          <input 
            type="text" 
            placeholder="Search queue by case or failure code..." 
            className="border-none outline-none bg-transparent text-[13px] text-gray-900 w-full placeholder:text-gray-400 font-medium"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div className="flex-1 overflow-y-auto bg-white">
          {loading ? (
            <div className="p-10 text-center text-gray-400 text-[13px] font-medium">Loading queue...</div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead className="bg-gray-50/80 text-[10px] uppercase tracking-wider text-gray-500 font-bold sticky top-0 z-10 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-2.5 font-bold">Case</th>
                  <th className="px-3 py-2.5 font-bold text-right">Amount</th>
                  <th className="px-3 py-2.5 font-bold">Failure</th>
                  <th className="px-3 py-2.5 font-bold text-center">Prob</th>
                  <th className="px-4 py-2.5 font-bold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((c) => {
                  const isSelected = c.scenario_key === id;
                  return (
                    <tr 
                      key={c.scenario_key}
                      onClick={() => navigate(`/queue/${c.scenario_key}`)}
                      className={`group cursor-pointer transition-colors ${isSelected ? 'bg-blue-50/60' : 'hover:bg-gray-50'}`}
                    >
                      <td className="px-4 py-3 align-top">
                        <div className={`text-[13px] font-bold ${isSelected ? 'text-blue-700' : 'text-gray-900'}`}>{c.title}</div>
                        <div className="text-[11px] text-gray-400 mt-0.5 font-medium">Action: Tomorrow 09:00</div>
                      </td>
                      <td className="px-3 py-3 align-top text-right">
                        <div className={`text-[13px] font-bold ${isSelected ? 'text-blue-700' : 'text-gray-900'}`}>₹{c.amount.toLocaleString(undefined, {minimumFractionDigits: 0})}</div>
                      </td>
                      <td className="px-3 py-3 align-top">
                        <div className="text-[11px] font-mono text-red-600 bg-red-50 border border-red-100 rounded px-1.5 py-0.5 inline-block truncate max-w-[120px]">{c.failure_code}</div>
                      </td>
                      <td className="px-3 py-3 align-top text-center">
                        {c.initial_probability > 0 ? (
                          <span className="text-[12px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                            {(c.initial_probability * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-[12px] text-gray-400 font-medium">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <Badge variant="low" className={`text-[10px] font-bold tracking-wider ${isSelected ? 'bg-blue-100 text-blue-700 border-blue-200' : ''}`}>READY</Badge>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </motion.div>

      <div className={`w-full xl:w-7/12 flex-col bg-[#f4f5f7] rounded-lg overflow-y-auto ${!id ? 'hidden xl:flex' : 'flex'}`}>
        <AnimatePresence mode="wait">
          {id ? (
            <motion.div key={id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="h-full flex justify-center w-full">
              <CaseDetail />
            </motion.div>
          ) : (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center h-full text-gray-400 gap-4 bg-white border border-gray-200 shadow-sm rounded-lg m-1">
              <div className="w-16 h-16 rounded-full bg-gray-50 border border-gray-200 flex items-center justify-center shadow-sm">
                <Inbox className="w-6 h-6 text-gray-400" />
              </div>
              <div className="text-[14px] font-semibold text-gray-500">Select a case from the queue to investigate</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
