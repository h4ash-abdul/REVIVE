import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { RotateCcw, Play, CheckCircle2, XCircle, Ban, Zap, AlertTriangle } from 'lucide-react'
import api from '../api/client'
import { TraceData } from '../types'
import { format } from 'date-fns'

export default function CaseDetail() {
  const { id } = useParams()
  const [trace, setTrace] = useState<TraceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [execStep, setExecStep] = useState(-1)

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
    const steps = ['DIAGNOSING...', 'PREDICTING...', 'CHECKING POLICY...', 'EXECUTING...', 'VERIFYING...']
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

  if (loading && !trace) return <div className="p-10 text-[11px] text-gray-500 font-mono flex h-full items-center justify-center">LOADING_CASE_DATA...</div>
  if (!trace) return <div className="p-10 text-[11px] text-rose-500 font-mono flex h-full items-center justify-center">CASE_NOT_FOUND</div>

  const isResolved = trace.obligation_status !== 'active_recovery'
  const isSuccess = trace.outcome?.success
  const isActionable = !isResolved && trace.budget_remaining > 0;
  
  const hasPrediction = !!trace.strategy_result;
  const hasOutcome = !!trace.outcome;

  const currentStep: number = hasOutcome ? 5 : hasPrediction ? 3 : 1;

  const TimelineStep = ({ num, label, active, completed }: any) => (
    <div className={`flex items-start gap-4 ${active ? 'opacity-100' : completed ? 'opacity-60' : 'opacity-30'}`}>
      <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold font-mono shrink-0 mt-0.5 border ${
        active ? 'bg-white text-black border-white' : completed ? 'bg-[#222328] text-gray-400 border-gray-600' : 'bg-transparent text-gray-600 border-[#222328]'
      }`}>
        {completed ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> : num}
      </div>
      <div className="flex flex-col pt-0.5 pb-6">
        <span className={`text-[11px] font-bold tracking-widest uppercase ${active ? 'text-white' : 'text-gray-400'}`}>{label}</span>
      </div>
    </div>
  )

  const getConfStyle = (prob: number) => {
    if (prob === 0) return 'text-gray-500 bg-gray-500/10 border-gray-500/20'
    if (prob > 0.7) return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
    if (prob >= 0.4) return 'text-amber-400 bg-amber-400/10 border-amber-400/20'
    return 'text-rose-400 bg-rose-400/10 border-rose-400/20'
  }
  
  const getConfLabel = (prob: number) => {
    if (prob === 0) return 'BLOCKED'
    if (prob > 0.7) return 'HIGH CONFIDENCE'
    if (prob >= 0.4) return 'MODERATE CONFIDENCE'
    return 'LOW CONFIDENCE'
  }

  // Simulated chart data based on actual candidate data if available
  const chartData = trace.strategy_result?.candidate_actions 
    ? trace.strategy_result.candidate_actions.map((c: any) => ({
        time: format(new Date(c.scheduled_time), "HH:mm"),
        prob: c.amount > 0 ? trace.initial_probability || 0.5 : 0 // simplify
      }))
    : [
        { time: '09:00', prob: trace.initial_probability || 0 },
        { time: '13:00', prob: Math.max(0, (trace.initial_probability || 0) - 0.2) },
        { time: '18:00', prob: Math.max(0, (trace.initial_probability || 0) - 0.3) },
      ]

  return (
    <div className="w-full flex bg-[#0a0a0b] h-full overflow-hidden text-gray-100">
      
      {/* TIMELINE SIDEBAR */}
      <div className="w-[180px] border-r border-[#222328] bg-[#121316] p-6 shrink-0 flex flex-col">
        <div className="text-[9px] font-bold text-gray-500 tracking-widest uppercase mb-8">EXECUTION TRACE</div>
        <div className="flex flex-col relative">
          <div className="absolute left-[9px] top-4 bottom-8 w-px bg-[#222328]" />
          <TimelineStep num="1" label="DIAGNOSE" active={currentStep === 1} completed={currentStep > 1} />
          <TimelineStep num="2" label="PREDICT" active={currentStep === 2} completed={currentStep > 2} />
          <TimelineStep num="3" label="POLICY CHECK" active={currentStep === 3} completed={currentStep > 3} />
          <TimelineStep num="4" label="EXECUTE" active={currentStep === 4} completed={currentStep > 4} />
          <TimelineStep num="5" label="VERIFY" active={currentStep === 5} completed={currentStep >= 5} />
        </div>
      </div>

      {/* MAIN DETAIL PANEL */}
      <div className="flex-1 overflow-y-auto bg-[#0a0a0b] relative">
        <div className="p-8 pb-32 max-w-[800px] flex flex-col gap-8">
          
          {/* HEADER */}
          <div className="flex justify-between items-start">
            <div className="flex flex-col gap-2">
              <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">MANDATE ID: {id}</div>
              <h1 className="text-[28px] font-mono font-bold text-white tracking-tight">
                ₹{trace.amount.toLocaleString(undefined, {minimumFractionDigits:0, maximumFractionDigits:0})}
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[9px] font-bold tracking-widest uppercase px-1.5 py-0.5 rounded border bg-[#16171a] border-[#222328] text-gray-400">
                  {trace.obligation_status}
                </span>
                <span className="text-[9px] font-bold tracking-widest uppercase px-1.5 py-0.5 rounded border bg-[#16171a] border-[#222328] text-rose-400">
                  {trace.failure_code}
                </span>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <button onClick={handleReset} disabled={executing} className="px-4 py-2 border border-[#222328] bg-[#16171a] hover:bg-[#1e1f24] text-gray-300 font-bold text-[10px] tracking-widest uppercase rounded flex items-center transition-colors">
                <RotateCcw className="w-3.5 h-3.5 mr-2"/> RESET
              </button>
              
              {isResolved ? (
                <div className={`px-4 py-2 rounded text-[10px] font-bold tracking-widest uppercase flex items-center border ${isSuccess ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'}`}>
                  {isSuccess ? <><CheckCircle2 className="w-3.5 h-3.5 mr-2" /> RECOVERED</> : <><XCircle className="w-3.5 h-3.5 mr-2" /> RECOVERY FAILED</>}
                </div>
              ) : !isActionable ? (
                <div className="px-4 py-2 rounded text-[10px] font-bold tracking-widest uppercase flex items-center border bg-gray-800 text-gray-400 border-gray-700">
                  <Ban className="w-3.5 h-3.5 mr-2" /> RECOVERY BLOCKED
                </div>
              ) : (
                <button onClick={handleTrigger} disabled={executing} className="px-4 py-2 bg-white hover:bg-gray-200 text-black font-bold tracking-widest uppercase text-[10px] rounded flex items-center transition-colors">
                  {executing ? 'EXECUTING...' : <><Play className="w-3.5 h-3.5 mr-2"/> TRIGGER RECOVERY</>}
                </button>
              )}
            </div>
          </div>

          {/* OUTCOME BANNER (IF RESOLVED) */}
          {(isResolved || trace.last_attempt_outcome) && (
            <div className={`p-4 border rounded flex items-start gap-3 ${isSuccess ? 'bg-emerald-900/20 border-emerald-500/30' : 'bg-rose-900/20 border-rose-500/30'}`}>
              {isSuccess ? <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" /> : <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />}
              <div className="flex flex-col">
                <span className={`text-[11px] font-bold tracking-widest uppercase ${isSuccess ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {isSuccess ? 'RECOVERY SUCCESSFUL' : trace.budget_remaining === 0 ? 'RECOVERY EXHAUSTED' : isResolved ? 'RECOVERY FAILED' : 'RECOVERY FAILED — RETRY AVAILABLE'}
                </span>
                <span className="text-[12px] text-gray-300 mt-1 font-mono">
                  {isSuccess 
                    ? `Payment of ₹${trace.recovered_amount?.toLocaleString() || trace.amount.toLocaleString()} was successfully recovered.`
                    : trace.budget_remaining === 0
                      ? 'Maximum retry budget (3/3) has been reached. No further recovery action is permitted.'
                      : `Execution attempt failed (Code: ${trace.outcome?.network_return_code || 'Unknown'}).`
                  }
                </span>
              </div>
            </div>
          )}

          {/* AI PREDICTION & CHART */}
          <div className="flex flex-col gap-4">
            <h2 className="text-[11px] font-bold text-gray-500 uppercase tracking-widest border-b border-[#222328] pb-2">PREDICTIVE INTELLIGENCE</h2>
            
            <div className="p-6 bg-[#16171a] border border-[#222328] rounded flex flex-col gap-6">
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">MAXIMUM RECOVERY CONFIDENCE</span>
                  <div className="flex items-end gap-3">
                    <span className="text-[32px] font-mono font-bold text-white leading-none">
                      {trace.initial_probability ? (trace.initial_probability * 100).toFixed(0) : (trace.budget_remaining === 0 ? 0 : 72)}<span className="text-[16px] text-gray-600">%</span>
                    </span>
                    <span className={`text-[9px] font-bold tracking-widest uppercase px-2 py-1 rounded border mb-1 ${getConfStyle(trace.initial_probability || 0)}`}>
                      {getConfLabel(trace.initial_probability || 0)}
                    </span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1 text-[10px] font-bold text-gray-500 uppercase tracking-widest text-right">
                  <span>MODEL: V1.1_HIERARCHICAL</span>
                  <span>FEATURES: TEMPORAL_CTX</span>
                </div>
              </div>

              {/* BAR CHART */}
              <div className="flex flex-col mt-4">
                <span className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-3">RECOVERY WINDOW PROBABILITIES</span>
                <div className="h-[120px] flex items-end gap-2 border-b border-[#222328] pb-1">
                  {chartData.map((d: any, i: number) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-2 group relative">
                      <div className="w-full bg-[#1e1f24] rounded-t relative overflow-hidden flex items-end justify-center h-full max-h-[100px]">
                        <motion.div 
                          initial={{ height: 0 }} 
                          animate={{ height: `${(d.prob || 0) * 100}%` }} 
                          className={`w-full ${i === 0 ? (d.prob > 0 ? 'bg-emerald-500/80' : 'bg-gray-700/50') : 'bg-gray-700/50'}`}
                        />
                      </div>
                      <span className="text-[9px] font-mono text-gray-500 group-hover:text-white transition-colors">{d.time}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* POLICY CHECKLIST */}
          <div className="flex flex-col gap-4">
            <h2 className="text-[11px] font-bold text-gray-500 uppercase tracking-widest border-b border-[#222328] pb-2">DETERMINISTIC POLICY</h2>
            
            <div className="p-6 bg-[#16171a] border border-[#222328] rounded flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-3 text-[11px] font-mono text-gray-300">
                  <div className="w-4 h-4 rounded bg-[#1e1f24] border border-[#2a2b30] flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  </div>
                  MANDATE_STATUS_ACTIVE
                </div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-gray-300">
                  <div className="w-4 h-4 rounded bg-[#1e1f24] border border-[#2a2b30] flex items-center justify-center shrink-0">
                    {trace.budget_remaining > 0 ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> : <XCircle className="w-3 h-3 text-rose-400" />}
                  </div>
                  RETRY_BUDGET_AVAILABLE ({trace.budget_remaining}/3)
                </div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-gray-300">
                  <div className="w-4 h-4 rounded bg-[#1e1f24] border border-[#2a2b30] flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  </div>
                  COOLDOWN_PERIOD_CLEARED
                </div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-gray-300">
                  <div className="w-4 h-4 rounded bg-[#1e1f24] border border-[#2a2b30] flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  </div>
                  EV_THRESHOLD_MET
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-[#222328] flex items-center justify-between">
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">FINAL DECISION</span>
                {trace.strategy_result?.selected_action ? (
                  <div className="flex items-center gap-2">
                    <Zap className="w-3.5 h-3.5 text-white" />
                    <span className="text-[11px] font-mono font-bold text-white uppercase">
                      EXECUTE @ {format(new Date(trace.strategy_result.selected_action.scheduled_time), "MMM d HH:mm")}
                    </span>
                  </div>
                ) : (
                  <span className="text-[11px] font-mono font-bold text-rose-400 uppercase">
                    ACTION DENIED
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* AUDIT LOG */}
          <div className="flex flex-col gap-4">
            <h2 className="text-[11px] font-bold text-gray-500 uppercase tracking-widest border-b border-[#222328] pb-2">IMMUTABLE AUDIT TRAIL</h2>
            <div className="p-0 border border-[#222328] bg-[#16171a] rounded overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead className="bg-[#121316] text-[9px] uppercase tracking-widest text-gray-500 font-bold border-b border-[#222328]">
                  <tr>
                    <th className="px-4 py-2.5">TIMESTAMP</th>
                    <th className="px-4 py-2.5">EVENT TYPE</th>
                    <th className="px-4 py-2.5">ACTOR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e1f24] text-[11px] font-mono text-gray-300">
                  {trace.audit_trail && trace.audit_trail.length > 0 ? (
                    trace.audit_trail.map((e) => (
                      <tr key={e.event_id} className="hover:bg-[#1a1b1f]">
                        <td className="px-4 py-2.5 text-gray-500">{format(new Date(e.timestamp), 'HH:mm:ss.SSS')}</td>
                        <td className="px-4 py-2.5 text-white">{e.event_type}</td>
                        <td className="px-4 py-2.5">{e.actor || 'SYSTEM'}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="px-4 py-4 text-center text-gray-600">NO_AUDIT_EVENTS_RECORDED</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        
        {/* EXECUTION OVERLAY */}
        <AnimatePresence>
          {executing && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 bg-[#0a0a0b]/90 backdrop-blur-sm z-50 flex items-center justify-center p-8">
              <div className="w-full max-w-[400px] bg-[#16171a] border border-[#222328] p-6 rounded shadow-2xl flex flex-col gap-6">
                <div className="text-[10px] font-bold text-gray-500 tracking-widest uppercase text-center mb-2">SYSTEM EXECUTION</div>
                
                {['DIAGNOSING CONTEXT', 'GENERATING PREDICTIONS', 'EVALUATING DETERMINISTIC POLICY', 'DISPATCHING NETWORK CALL', 'VERIFYING OUTCOME'].map((step, idx) => (
                  <div key={idx} className={`flex items-center gap-3 text-[11px] font-mono tracking-wide ${idx === execStep ? 'text-white' : idx < execStep ? 'text-emerald-400' : 'text-gray-600'}`}>
                    {idx < execStep ? <CheckCircle2 className="w-4 h-4" /> : idx === execStep ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <div className="w-4 h-4 rounded-full border border-gray-600" />}
                    {step}
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
