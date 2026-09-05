import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Badge } from '../components/ui'
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

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[1200px] w-full">
      <div className="flex flex-col gap-2">
        <h1 className="text-[32px] font-bold text-gray-900 tracking-tight">REVIVE<span className="text-gray-400 font-normal"> / Recovery Operations</span></h1>
        <p className="text-[14px] text-blue-600 font-semibold tracking-wide mb-4">ADAPTIVE AI REVENUE RECOVERY AGENT</p>
        
        <div>
          <Button variant="primary" onClick={() => navigate('/queue')} className="px-6 py-3 font-semibold tracking-wide bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-sm transition-all">
            OPEN RECOVERY OPERATIONS <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>

      <div className="text-[11px] text-gray-400 font-bold tracking-wider uppercase -mb-6">
        SIMULATED OPERATIONAL SUMMARY
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card 
          className="p-6 flex flex-col gap-2 cursor-pointer group hover:border-gray-400 transition-all shadow-sm hover:shadow-md"
          onClick={() => navigate('/queue?filter=at-risk')}
        >
          <div className="flex justify-between items-center">
            <div className="text-[12px] font-bold text-gray-500 uppercase tracking-wider">Revenue at Risk</div>
            <ArrowUpRight className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
          </div>
          <div className="text-[28px] font-bold text-gray-900 mt-1">₹128,368<span className="text-[16px] text-gray-400 font-normal">.32</span></div>
          <div className="text-[12px] text-gray-500 flex items-center gap-1 mt-2">
            <AlertCircle className="w-3.5 h-3.5 text-orange-500" /> Action required
          </div>
        </Card>
        
        <Card 
          className="p-6 flex flex-col gap-2 cursor-pointer group hover:border-gray-400 transition-all shadow-sm hover:shadow-md"
          onClick={() => navigate('/queue?filter=recovered')}
        >
          <div className="flex justify-between items-center">
            <div className="text-[12px] font-bold text-gray-500 uppercase tracking-wider">Recovered</div>
            <ArrowUpRight className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
          </div>
          <div className="text-[28px] font-bold text-green-700 mt-1">₹50,192<span className="text-[16px] text-green-700/60 font-normal">.12</span></div>
          <div className="text-[12px] text-green-700/80 flex items-center gap-1 mt-2 font-medium">
            +16.43% vs heuristics
          </div>
        </Card>
        
        <Card 
          className="p-6 flex flex-col gap-2 cursor-pointer group hover:border-gray-400 transition-all shadow-sm hover:shadow-md"
          onClick={() => navigate('/evidence')}
        >
          <div className="flex justify-between items-center">
            <div className="text-[12px] font-bold text-gray-500 uppercase tracking-wider">Recovery Rate</div>
            <ArrowUpRight className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
          </div>
          <div className="text-[28px] font-bold text-gray-900 mt-1">39.3<span className="text-[16px] text-gray-400 font-normal">%</span></div>
          <div className="text-[12px] text-gray-500 flex items-center gap-1 mt-2">
            Last 60 days
          </div>
        </Card>
        
        <Card 
          className="p-6 flex flex-col gap-2 cursor-pointer group hover:border-gray-400 transition-all shadow-sm hover:shadow-md"
          onClick={() => navigate('/queue?filter=active')}
        >
          <div className="flex justify-between items-center">
            <div className="text-[12px] font-bold text-gray-500 uppercase tracking-wider">Actionable Cases</div>
            <ArrowUpRight className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
          </div>
          <div className="text-[28px] font-bold text-gray-900 mt-1">417</div>
          <div className="text-[12px] text-gray-500 flex items-center gap-1 mt-2">
            <Clock className="w-3.5 h-3.5" /> Pending execution
          </div>
        </Card>
      </div>

      <div className="flex flex-col gap-6 mt-6">
        <div className="flex items-center justify-between">
          <h2 className="text-[16px] font-bold text-gray-900">READY FOR RECOVERY</h2>
          <span className="text-[13px] text-blue-600 font-medium cursor-pointer hover:underline" onClick={() => navigate('/queue')}>View all {activeCases.length}</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-4">
          {loading ? (
            <div className="text-[14px] text-gray-500 col-span-3 text-center py-10">Loading active cases...</div>
          ) : readyCases.map(c => (
            <Card key={c.scenario_key} className="p-6 flex flex-col gap-4 shadow-sm border border-gray-200">
              <div className="flex justify-between items-start">
                <div className="font-bold text-[15px] text-gray-900">{c.title}</div>
                <div className="font-bold text-[16px] text-gray-900">₹{c.amount.toLocaleString(undefined, {minimumFractionDigits: 0})}</div>
              </div>
              
              <div className="flex flex-col gap-3 mt-2">
                <div className="flex justify-between items-center text-[13px]">
                  <span className="text-gray-500 font-medium">Failure</span>
                  <Badge variant="critical" className="font-mono text-[10px] uppercase tracking-wider bg-red-50 text-red-700 border-red-200">{c.failure_code}</Badge>
                </div>
                <div className="flex justify-between items-center text-[13px]">
                  <span className="text-gray-500 font-medium">Probability</span>
                  <span className="text-blue-600 font-bold bg-blue-50 px-2 py-0.5 rounded text-[12px]">{(c.initial_probability * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between items-center text-[13px]">
                  <span className="text-gray-500 font-medium">Action</span>
                  <span className="text-gray-900 font-medium flex items-center gap-1"><Clock className="w-3.5 h-3.5 text-gray-400"/> Tomorrow 09:00</span>
                </div>
              </div>
              
              <div className="mt-4 pt-4 border-t border-gray-100">
                <Button 
                  className="w-full justify-between bg-gray-50 hover:bg-gray-100 text-gray-700 font-semibold border border-gray-200 transition-colors" 
                  onClick={() => navigate(`/queue/${c.scenario_key}`)}
                >
                  REVIEW CASE <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-700" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
