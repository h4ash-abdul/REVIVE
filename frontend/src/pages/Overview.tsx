import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Badge } from '../components/ui'
import api from '../api/client'
import { DemoCase } from '../types'
import { ChevronRight } from 'lucide-react'

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
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[1000px] w-full">
      <div className="flex flex-col gap-2">
        <h1 className="text-[28px] font-semibold text-textPrimary tracking-tight">REVIVE</h1>
        <p className="text-[14px] text-textSecondary font-medium tracking-wide text-accent mb-2">ADAPTIVE AI REVENUE RECOVERY AGENT</p>
        <p className="text-[16px] text-textPrimary max-w-[600px] leading-relaxed">
          Turn failed recurring payments into recoverable revenue with prediction, policy and auditable execution.
        </p>
        
        <div className="mt-4">
          <Button variant="primary" onClick={() => navigate('/queue')} className="px-6 py-3 font-semibold tracking-wide">
            OPEN RECOVERY OPERATIONS <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-5">
        <Card 
          className="p-5 flex flex-col gap-3 cursor-pointer hover:border-borderStrong hover:bg-panelAlt transition-colors"
          onClick={() => navigate('/queue?filter=at-risk')}
        >
          <div className="text-[10.5px] font-semibold text-textTertiary uppercase tracking-[0.5px]">Revenue at Risk</div>
          <div className="text-[24px] font-semibold">₹128,368.32</div>
        </Card>
        
        <Card 
          className="p-5 flex flex-col gap-3 cursor-pointer hover:border-borderStrong hover:bg-panelAlt transition-colors"
          onClick={() => navigate('/queue?filter=recovered')}
        >
          <div className="text-[10.5px] font-semibold text-textTertiary uppercase tracking-[0.5px]">Recovered</div>
          <div className="text-[24px] font-semibold text-success">₹50,192.12</div>
        </Card>
        
        <Card 
          className="p-5 flex flex-col gap-3 cursor-pointer hover:border-borderStrong hover:bg-panelAlt transition-colors"
          onClick={() => navigate('/evidence')}
        >
          <div className="text-[10.5px] font-semibold text-textTertiary uppercase tracking-[0.5px]">Recovery Rate</div>
          <div className="text-[24px] font-semibold">39.3%</div>
        </Card>
        
        <Card 
          className="p-5 flex flex-col gap-3 cursor-pointer hover:border-borderStrong hover:bg-panelAlt transition-colors"
          onClick={() => navigate('/queue?filter=active')}
        >
          <div className="text-[10.5px] font-semibold text-textTertiary uppercase tracking-[0.5px]">Active Cases</div>
          <div className="text-[24px] font-semibold">417</div>
        </Card>
      </div>
      
      <div className="text-[10px] text-textTertiary font-medium tracking-wider uppercase -mt-4">
        SIMULATED / SYNTHETIC EVALUATION
      </div>

      <div className="flex flex-col gap-6 mt-6">
        <h2 className="text-[14px] font-semibold text-textPrimary">READY FOR RECOVERY</h2>
        
        <div className="flex gap-5 overflow-x-auto pb-4">
          {loading ? (
            <div className="text-[12px] text-textSecondary">Loading...</div>
          ) : readyCases.map(c => (
            <Card key={c.scenario_key} className="w-[300px] shrink-0 p-5 flex flex-col gap-4">
              <div className="flex justify-between items-start">
                <div className="font-semibold text-[14px]">{c.title}</div>
                <div className="font-semibold text-[14px]">₹{c.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
              </div>
              
              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-center text-[11px]">
                  <span className="text-textSecondary">Failure</span>
                  <Badge variant="critical">{c.failure_code}</Badge>
                </div>
                <div className="flex justify-between items-center text-[11px]">
                  <span className="text-textSecondary">Recovery Probability</span>
                  <span className="text-elevated font-semibold">{(c.initial_probability * 100).toFixed(0)}%</span>
                </div>
              </div>
              
              <div className="mt-2 pt-4 border-t border-borderRef">
                <Button 
                  className="w-full justify-between" 
                  onClick={() => navigate(`/queue/${c.scenario_key}`)}
                >
                  REVIEW CASE <ChevronRight className="w-3.5 h-3.5 text-textTertiary" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
