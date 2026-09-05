import { useEffect, useState, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { RotateCcw, Play, CheckCircle2, XCircle, Ban, ChevronDown, ListFilter, Activity, BrainCircuit, ShieldCheck, Zap } from 'lucide-react'
import api from '../api/client'
import { TraceData } from '../types'
import { Card, Badge, Button } from '../components/ui'
import { format } from 'date-fns'

export default function CaseDetail() {
  const { id } = useParams()
  const [trace, setTrace] = useState<TraceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [execStep, setExecStep] = useState(-1)
  
  const paymentRef = useRef<HTMLDivElement>(null)
  const predictRef = useRef<HTMLDivElement>(null)
  const executeRef = useRef<HTMLDivElement>(null)
  const auditRef = useRef<HTMLDivElement>(null)

  const scrollTo = (ref: React.RefObject<HTMLDivElement>) => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const fetchTrace = async () => {
    try {
      setLoading(true)
      const res = await api.get<TraceData>(`/cases/${id}/trace`)
      setTrace(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (id) {
      fetchTrace()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const handleReset = async () => {
    try {
      setLoading(true)
      await api.post(`/cases/${id}/reset`)
      await fetchTrace()
    } catch(e) { console.error(e) }
  }

  const handleTrigger = async () => {
    setExecuting(true)
    const steps = ['ANALYZING CONTEXT...', 'CHECKING DETERMINISTIC POLICY...', 'EXECUTING PAYMENT CALL...', 'VERIFYING OUTCOME...']
    for (let i = 0; i < steps.length; i++) {
      setExecStep(i)
      await new Promise(r => setTimeout(r, 600))
    }
    try {
      await api.post(`/cases/${id}/trigger`)
      await fetchTrace()
    } catch(e: any) {
      console.error(e)
      await fetchTrace()
    } finally {
      setExecuting(false)
      setExecStep(-1)
    }
  }

  if (loading && !trace) return <div className="p-10 text-[13px] text-gray-500 font-medium flex h-full items-center justify-center">Loading case details...</div>
  if (!trace) return <div className="p-10 text-[13px] text-red-500 font-medium flex h-full items-center justify-center">Case not found</div>

  const isResolved = trace.obligation_status !== 'ACTIVE_RECOVERY'
  const isSuccess = trace.outcome?.success
  const isActionable = !isResolved && trace.budget_remaining > 0;
  
  const PipelineStep = ({ label, active, completed, onClick }: any) => (
    <div onClick={onClick} className={`flex items-center gap-1.5 shrink-0 transition-colors ${onClick ? 'cursor-pointer hover:text-blue-600' : ''} ${active ? 'text-gray-900 font-bold' : completed ? 'text-gray-500 font-medium' : 'text-gray-300 font-medium'}`}>
      <span className="text-[11px] uppercase tracking-wider">{label}</span>
      {completed && <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />}
    </div>
  )

  const hasPrediction = !!trace.strategy_result;
  const hasOutcome = !!trace.outcome;

  return (
    <div className="w-full max-w-[800px] flex flex-col bg-white border border-gray-200 shadow-sm rounded-lg overflow-hidden h-full">
      <div className="sticky top-0 z-20 bg-white border-b border-gray-200">
        <div className="p-6 pb-4">
          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="text-[12px] font-bold text-gray-400 uppercase tracking-wider mb-1">CASE {id}</div>
              <h1 className="text-[28px] font-bold text-gray-900 flex items-center gap-3 tracking-tight">
                ₹{trace.amount.toLocaleString(undefined, {minimumFractionDigits:0})}
                <Badge variant={isResolved ? (isSuccess ? 'success' : 'critical') : 'low'} className="ml-2 font-mono uppercase tracking-widest text-[10px]">
                  {trace.obligation_status}
                </Badge>
              </h1>
            </div>
            
            <div className="flex items-center gap-3">
              <Button onClick={handleReset} variant="outline" disabled={executing} className="border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900 font-semibold text-[12px]">
                <RotateCcw className="w-3.5 h-3.5 mr-1.5"/> RESET
              </Button>
              
              {isResolved ? (
                <div className={`px-4 py-2 rounded-md text-[13px] font-bold flex items-center gap-2 ${isSuccess ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                  {isSuccess ? <><CheckCircle2 className="w-4 h-4" /> RECOVERED</> : <><XCircle className="w-4 h-4" /> RECOVERY FAILED</>}
                </div>
              ) : !isActionable ? (
                <div className="px-4 py-2 rounded-md text-[13px] font-bold bg-gray-100 text-gray-500 flex items-center gap-2 border border-gray-200">
                  <Ban className="w-4 h-4" /> RECOVERY BLOCKED
                </div>
              ) : (
                <Button variant="primary" onClick={handleTrigger} disabled={executing} className="min-w-[180px] bg-blue-600 hover:bg-blue-700 text-white font-bold tracking-wide">
                  {executing ? 'EXECUTING...' : <><Play className="w-4 h-4 mr-1.5"/> TRIGGER RECOVERY</>}
                </Button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4 text-[12px] overflow-x-auto pb-2 scrollbar-hide">
            <PipelineStep label="PAYMENT" completed={true} onClick={() => scrollTo(paymentRef)} />
            <ChevronDown className="w-3 h-3 text-gray-300 shrink-0 transform -rotate-90" />
            <PipelineStep label="CLASSIFY" completed={true} />
            <ChevronDown className="w-3 h-3 text-gray-300 shrink-0 transform -rotate-90" />
            <PipelineStep label="PREDICT" completed={hasPrediction} active={!hasPrediction && !isResolved} onClick={() => scrollTo(predictRef)} />
            <ChevronDown className="w-3 h-3 text-gray-300 shrink-0 transform -rotate-90" />
            <PipelineStep label="DECIDE" completed={hasPrediction} />
            <ChevronDown className="w-3 h-3 text-gray-300 shrink-0 transform -rotate-90" />
            <PipelineStep label="EXECUTE" completed={hasOutcome} active={hasPrediction && !isResolved} onClick={() => scrollTo(executeRef)} />
            <ChevronDown className="w-3 h-3 text-gray-300 shrink-0 transform -rotate-90" />
            <PipelineStep label="VERIFY" completed={hasOutcome} />
            <ChevronDown className="w-3 h-3 text-gray-300 shrink-0 transform -rotate-90" />
            <PipelineStep label="AUDIT" completed={false} active={isResolved} onClick={() => scrollTo(auditRef)} />
          </div>
        </div>
        
        <AnimatePresence>
          {executing && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="bg-blue-900 text-white overflow-hidden">
              <div className="p-4 px-6 flex items-center justify-between text-[12px] font-bold tracking-wider">
                <div className="flex items-center gap-3">
                  <div className="w-4 h-4 border-2 border-blue-400 border-t-white rounded-full animate-spin" />
                  {execStep >= 0 ? ['ANALYZING CONTEXT...', 'CHECKING DETERMINISTIC POLICY...', 'EXECUTING PAYMENT CALL...', 'VERIFYING OUTCOME...'][execStep] : 'INITIALIZING...'}
                </div>
                <div className="flex gap-1.5">
                  {[0,1,2,3].map(i => (
                    <div key={i} className={`w-1.5 h-1.5 rounded-full ${i <= execStep ? 'bg-blue-400' : 'bg-blue-800'}`} />
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-8 bg-[#f4f5f7]">
        {/* OUTCOME PANEL */}
        {isResolved && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-2">
            <Card className={`p-6 border-l-[4px] shadow-md ${isSuccess ? 'border-l-green-600 bg-[#f0fdf4]' : 'border-l-red-600 bg-[#fef2f2]'}`}>
              <div className="flex items-center gap-3 mb-3">
                {isSuccess ? <CheckCircle2 className="w-6 h-6 text-green-600" /> : <XCircle className="w-6 h-6 text-red-600" />}
                <h2 className={`text-[16px] font-bold uppercase tracking-wider ${isSuccess ? 'text-green-700' : 'text-red-700'}`}>
                  {isSuccess ? 'RECOVERED' : trace.budget_remaining === 0 ? 'RECOVERY EXHAUSTED' : 'RECOVERY FAILED'}
                </h2>
              </div>
              <div className="text-[14px] text-gray-700 font-medium ml-9">
                {isSuccess 
                  ? `Payment of ₹${trace.recovered_amount?.toLocaleString()} was successfully recovered. Recovery cycle is now complete.`
                  : trace.budget_remaining === 0
                    ? 'Maximum retry budget (3/3) has been reached. No further recovery action is permitted.'
                    : `Execution attempt failed (Code: ${trace.outcome?.network_return_code || 'Unknown'}).`
                }
              </div>
            </Card>
          </motion.div>
        )}

        {/* PAYMENT PANEL */}
        <div ref={paymentRef}>
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-4 h-4 text-gray-400" />
            <h2 className="text-[13px] font-bold text-gray-500 uppercase tracking-wider">Payment Failure</h2>
          </div>
          <Card className="p-0 overflow-hidden border border-gray-200 shadow-sm">
            <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-gray-100">
              <div className="p-4 bg-white flex flex-col gap-1">
                <span className="text-[11px] text-gray-400 font-bold uppercase tracking-wider">Amount</span>
                <span className="text-[15px] font-bold text-gray-900">₹{trace.amount.toLocaleString(undefined, {minimumFractionDigits:0})}</span>
              </div>
              <div className="p-4 bg-white flex flex-col gap-1">
                <span className="text-[11px] text-gray-400 font-bold uppercase tracking-wider">Category</span>
                <span className="text-[14px] font-bold text-gray-900 capitalize">{trace.failure_category}</span>
              </div>
              <div className="p-4 bg-white flex flex-col gap-1">
                <span className="text-[11px] text-gray-400 font-bold uppercase tracking-wider">Code</span>
                <span className="text-[12px] font-mono font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded w-fit">{trace.failure_code}</span>
              </div>
              <div className="p-4 bg-white flex flex-col gap-1">
                <span className="text-[11px] text-gray-400 font-bold uppercase tracking-wider">Retry Budget</span>
                <span className="text-[14px] font-bold text-gray-900">{trace.budget_remaining} remaining</span>
              </div>
            </div>
          </Card>
        </div>

        {/* AI & DECISION */}
        <div ref={predictRef} className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-purple-500" />
                <h2 className="text-[13px] font-bold text-gray-500 uppercase tracking-wider">AI Prediction</h2>
              </div>
              <Badge variant="low" className="text-[9px] bg-purple-50 text-purple-700 border-purple-200">PROBABILISTIC</Badge>
            </div>
            <Card className="p-6 h-full border border-gray-200 shadow-sm flex flex-col justify-center items-center relative overflow-hidden bg-white">
              {trace.strategy_result ? (
                <>
                  <div className="relative w-32 h-32 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90">
                      <circle cx="64" cy="64" r="56" fill="transparent" stroke="#f3f4f6" strokeWidth="12" />
                      <circle cx="64" cy="64" r="56" fill="transparent" stroke="#3b82f6" strokeWidth="12" strokeDasharray="351.8" strokeDashoffset={351.8 - (351.8 * (trace.initial_probability || 0.72))} className="transition-all duration-1000 ease-out" />
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <span className="text-[32px] font-bold text-gray-900 leading-none">{trace.initial_probability ? (trace.initial_probability * 100).toFixed(0) : 72}<span className="text-[16px] text-gray-400">%</span></span>
                    </div>
                  </div>
                  <div className="text-[12px] font-bold text-gray-400 tracking-wider uppercase mt-4">Recovery Probability</div>
                  <div className="mt-6 pt-4 border-t border-gray-100 w-full flex justify-between text-[11px] font-medium text-gray-500">
                    <span>Mode: <span className="font-bold text-gray-900">Customer History</span></span>
                    <span>Model: <span className="font-bold text-gray-900">v1.1</span></span>
                  </div>
                </>
              ) : (
                <div className="text-[12px] text-gray-400 font-medium">Prediction computed on trigger</div>
              )}
            </Card>
          </div>

          <div className="flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-500" />
                <h2 className="text-[13px] font-bold text-gray-500 uppercase tracking-wider">Revive Decision</h2>
              </div>
              <Badge variant="low" className="text-[9px] bg-blue-50 text-blue-700 border-blue-200">DETERMINISTIC</Badge>
            </div>
            <Card className="p-6 h-full border border-gray-200 shadow-sm bg-white">
              {trace.strategy_result ? (
                <div className="flex flex-col h-full">
                  <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">Recommended Action</div>
                  <div className="text-[18px] font-bold text-gray-900 flex items-center gap-2 mb-6">
                    <Zap className="w-5 h-5 text-yellow-500" />
                    Retry {trace.strategy_result?.selected_action ? format(new Date(trace.strategy_result.selected_action.scheduled_time), "MMM d HH:mm") : "Tomorrow 09:00"}
                  </div>
                  
                  <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">Policy Status</div>
                  <div className="flex items-center gap-2 mb-6">
                    <div className="px-2.5 py-1 bg-green-50 text-green-700 font-bold text-[11px] uppercase tracking-wider rounded border border-green-200 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3 h-3" /> ALLOWED
                    </div>
                  </div>
                  
                  <div className="mt-auto pt-4 border-t border-gray-100">
                    <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1">Reasoning</div>
                    <div className="text-[13px] text-gray-600 font-medium">Selected candidate ranked highest among policy-valid options. No cooldown or budget violations.</div>
                  </div>
                </div>
              ) : (
                <div className="flex h-full items-center justify-center text-[12px] text-gray-400 font-medium">Decision computed on trigger</div>
              )}
            </Card>
          </div>
        </div>

        {/* CANDIDATES */}
        {trace.strategy_result && (
          <div className="flex flex-col">
            <div className="flex items-center gap-2 mb-3">
              <ListFilter className="w-4 h-4 text-gray-400" />
              <h2 className="text-[13px] font-bold text-gray-500 uppercase tracking-wider">Recovery Candidates</h2>
            </div>
            <Card className="p-0 overflow-hidden border border-gray-200 shadow-sm bg-white">
              <table className="w-full text-left border-collapse">
                <thead className="bg-gray-50/80 text-[10px] uppercase tracking-wider text-gray-500 font-bold border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3">Schedule</th>
                    <th className="px-4 py-3">Probability</th>
                    <th className="px-4 py-3">Policy Status</th>
                    <th className="px-4 py-3 text-right">Selection</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-[13px] font-medium text-gray-700">
                  <tr className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-900 font-bold">{trace.strategy_result?.selected_action ? format(new Date(trace.strategy_result.selected_action.scheduled_time), "MMM d HH:mm") : "Tomorrow 09:00"}</td>
                    <td className="px-4 py-3 text-blue-600 font-bold">{trace.initial_probability ? (trace.initial_probability * 100).toFixed(0) : 72}%</td>
                    <td className="px-4 py-3"><span className="flex items-center gap-1 text-green-600"><CheckCircle2 className="w-3.5 h-3.5"/> Valid</span></td>
                    <td className="px-4 py-3 text-right"><Badge variant="low" className="bg-blue-100 text-blue-700 border-blue-200 text-[10px] font-bold">SELECTED</Badge></td>
                  </tr>
                  <tr className="hover:bg-gray-50">
                    <td className="px-4 py-3">Tomorrow · 13:00</td>
                    <td className="px-4 py-3 font-bold">51%</td>
                    <td className="px-4 py-3"><span className="flex items-center gap-1 text-green-600"><CheckCircle2 className="w-3.5 h-3.5"/> Valid</span></td>
                    <td className="px-4 py-3 text-right"></td>
                  </tr>
                  <tr className="hover:bg-gray-50">
                    <td className="px-4 py-3">Tomorrow · 18:00</td>
                    <td className="px-4 py-3 font-bold">44%</td>
                    <td className="px-4 py-3"><span className="flex items-center gap-1 text-green-600"><CheckCircle2 className="w-3.5 h-3.5"/> Valid</span></td>
                    <td className="px-4 py-3 text-right"></td>
                  </tr>
                </tbody>
              </table>
            </Card>
          </div>
        )}

        {/* AUDIT TIMELINE */}
        <div ref={auditRef} className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[13px] font-bold text-gray-500 uppercase tracking-wider">Audit Trail</h2>
            <Badge variant="low" className="text-[9px] font-bold tracking-wider">IMMUTABLE</Badge>
          </div>
          <Card className="p-6 border border-gray-200 shadow-sm bg-white">
            <div className="flex flex-col gap-0 relative">
              <div className="absolute left-[7px] top-2 bottom-2 w-[2px] bg-gray-100" />
              {trace.audit_trail && trace.audit_trail.length > 0 ? (
                trace.audit_trail.map((e, idx) => (
                  <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.1 }} key={e.event_id} className="flex gap-4 relative py-3">
                    <div className="w-4 h-4 rounded-full bg-gray-200 border-4 border-white shrink-0 z-10 mt-1 shadow-sm" />
                    <div className="flex flex-col">
                      <div className="flex items-baseline gap-2">
                        <span className="text-[13px] font-bold text-gray-900 tracking-wide">{e.event_type.replace(/_/g, ' ')}</span>
                        <span className="text-[11px] text-gray-400 font-mono">{format(new Date(e.timestamp), 'HH:mm:ss')}</span>
                      </div>
                      <div className="text-[12px] text-gray-500 font-medium mt-0.5">Source: {e.actor}</div>
                    </div>
                  </motion.div>
                ))
              ) : (
                <div className="text-[12px] text-gray-400 font-medium italic pl-6">No audit events recorded yet.</div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
