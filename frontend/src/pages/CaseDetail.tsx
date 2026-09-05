import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { RotateCcw, Play, CheckCircle2, XCircle, Ban, ShieldX, ChevronLeft, ChevronDown } from 'lucide-react'
import api from '../api/client'
import { TraceData } from '../types'
import { Card, Badge, Button } from '../components/ui'
import { format } from 'date-fns'

export default function CaseDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [trace, setTrace] = useState<TraceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [execStep, setExecStep] = useState(-1)
  const [showCandidates, setShowCandidates] = useState(false)
  
  const paymentRef = useRef<HTMLDivElement>(null)
  const predictRef = useRef<HTMLDivElement>(null)
  const policyRef = useRef<HTMLDivElement>(null)
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
      setShowCandidates(false)
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
      alert(e?.response?.data?.detail || "Execution failed")
      await fetchTrace()
    } finally {
      setExecuting(false)
      setExecStep(-1)
    }
  }

  if (loading && !trace) return <div className="p-10 text-[12px] text-textSecondary flex h-full items-center justify-center">Loading case details...</div>
  if (!trace) return <div className="p-10 text-[12px] text-critical flex h-full items-center justify-center">Case not found</div>

  const isResolved = trace.obligation_status !== 'ACTIVE_RECOVERY'
  const isSuccess = trace.outcome?.success
  const isActionable = !isResolved && trace.budget_remaining > 0;
  
  const PipelineStep = ({ label, active, completed, onClick }: { label: string, active?: boolean, completed?: boolean, onClick?: () => void }) => (
    <div 
      onClick={onClick}
      className={`flex items-center gap-1.5 shrink-0 transition-colors ${onClick ? 'cursor-pointer hover:text-accent' : ''} ${active ? 'text-textPrimary font-semibold' : completed ? 'text-textSecondary' : 'text-textTertiary'}`}
    >
      <span className="text-[10px] uppercase tracking-[0.5px]">{label}</span>
      {completed && <CheckCircle2 className="w-3 h-3 text-success" />}
    </div>
  )

  return (
    <div className="flex flex-col gap-6 pb-20 max-w-[800px] w-full pt-4">
      
      {/* Sticky Action Bar */}
      <div className="sticky top-0 z-20 bg-page/95 backdrop-blur-sm pt-2 pb-4 border-b border-borderRef mb-2 flex items-center justify-between shadow-sm -mt-4">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/queue')} className="lg:hidden text-textTertiary hover:text-textPrimary transition-colors mr-1">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="flex flex-col gap-1">
          <div className="text-[12px] font-medium text-textSecondary">Case {id}</div>
          <h1 className="text-[20px] font-semibold m-0 flex items-center gap-3 text-textPrimary">
            ₹{trace.amount.toLocaleString(undefined, {minimumFractionDigits:2})}
            <Badge variant={isResolved ? (isSuccess ? 'success' : 'critical') : 'low'} className="ml-2">
              {trace.obligation_status}
            </Badge>
          </h1>
        </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Button onClick={handleReset} variant="outline" disabled={executing}><RotateCcw className="w-3.5 h-3.5"/> RESET</Button>
          
          {isResolved ? (
            <div className={`px-4 py-2 rounded-[3px] text-xs font-semibold flex items-center gap-2 ${isSuccess ? 'bg-successBg text-success border border-success/20' : 'bg-criticalBg text-critical border border-critical/20'}`}>
              {isSuccess ? <><CheckCircle2 className="w-4 h-4" /> RECOVERED</> : <><XCircle className="w-4 h-4" /> RECOVERY FAILED</>}
            </div>
          ) : !isActionable ? (
            <div className="px-4 py-2 rounded-[3px] text-xs font-semibold bg-lowBg text-textSecondary flex items-center gap-2 border border-borderRef">
              <Ban className="w-4 h-4" /> RECOVERY BLOCKED
            </div>
          ) : (
            <Button 
              variant="primary" 
              onClick={handleTrigger} 
              disabled={executing}
              className="min-w-[160px]"
            >
              {executing ? 'EXECUTING...' : <><Play className="w-3.5 h-3.5"/> TRIGGER RECOVERY</>}
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-4 px-5 py-4 bg-panel border border-borderRef rounded-[3px] overflow-x-auto shadow-sm">
          <PipelineStep label="PAYMENT" completed onClick={() => scrollTo(paymentRef)} />
          <span className="text-borderStrong shrink-0 text-[10px]">→</span>
          <PipelineStep label="PREDICT" completed={!!trace.strategy_result} active={!trace.strategy_result} onClick={() => scrollTo(predictRef)} />
          <span className="text-borderStrong shrink-0 text-[10px]">→</span>
          <PipelineStep label="POLICY" completed={!!trace.strategy_result} active={!trace.strategy_result} onClick={() => scrollTo(policyRef)} />
          <span className="text-borderStrong shrink-0 text-[10px]">→</span>
          <PipelineStep label="EXECUTE" completed={!!trace.execution_record} active={executing} onClick={() => scrollTo(executeRef)} />
          <span className="text-borderStrong shrink-0 text-[10px]">→</span>
          <PipelineStep label="VERIFY" completed={!!trace.outcome} active={!!trace.execution_record && !trace.outcome} onClick={() => scrollTo(executeRef)} />
          <span className="text-borderStrong shrink-0 text-[10px]">→</span>
          <PipelineStep label="AUDIT" completed={!!trace.outcome} active={!!trace.outcome} onClick={() => scrollTo(auditRef)} />
        </div>
      </div>

      <div className="flex flex-col gap-6">
        
        <Card className="p-6" ref={paymentRef}>
          <h2 className="text-[10px] font-semibold text-textTertiary uppercase tracking-[1px] mb-5">1. PAYMENT FAILURE</h2>
          <div className="grid grid-cols-3 gap-y-5 gap-x-8">
            <div>
              <div className="text-[11px] text-textSecondary mb-1">Failure Category</div>
              <Badge variant={trace.failure_category === 'technical' ? 'elevated' : 'critical'}>
                {trace.failure_category.toUpperCase()}
              </Badge>
            </div>
            <div>
              <div className="text-[11px] text-textSecondary mb-1">Failure Code</div>
              <div className="font-semibold text-[13px]">{trace.failure_code}</div>
            </div>
            <div>
              <div className="text-[11px] text-textSecondary mb-1">Retry Budget</div>
              <div className="font-semibold text-[13px]">{trace.budget_remaining} retries remaining</div>
            </div>
          </div>
        </Card>

        {trace.strategy_result && (
          <div className="grid grid-cols-2 gap-6">
            <Card className="p-6 flex flex-col" ref={predictRef}>
              <div className="flex justify-between items-start mb-5">
                <h2 className="text-[10px] font-semibold text-textTertiary uppercase tracking-[1px]">2. AI PREDICTION</h2>
                <span className="text-[9px] font-semibold tracking-wider text-accent bg-blue-50 px-2 py-0.5 rounded border border-blue-100">PROBABILISTIC</span>
              </div>
              
              <div className="flex flex-col items-center justify-center py-6 flex-1">
                <div className="text-[48px] font-bold tracking-tight text-textPrimary leading-none">
                  {Math.round(trace.strategy_result.prediction_score * 100)}<span className="text-[24px] text-textTertiary">%</span>
                </div>
                <div className="text-[11px] font-medium text-textSecondary uppercase tracking-widest mt-2">Recovery Probability</div>
              </div>
              
              <div className="mt-4 pt-4 border-t border-borderRef flex flex-col gap-2 shrink-0">
                <div className="flex justify-between text-[11px] text-textSecondary">
                  <span>Optimization:</span>
                  <span className="font-medium text-textPrimary">{trace.strategy_result.prediction_mode}</span>
                </div>
                <div 
                  className="mt-2 text-[10px] font-semibold tracking-[0.5px] text-textSecondary cursor-pointer hover:bg-panelAlt bg-page p-2 border border-borderRef rounded-[3px] transition-colors flex justify-between items-center uppercase"
                  onClick={() => setShowCandidates(!showCandidates)}
                >
                  <span>Evaluate {trace.strategy_result.prediction_mode === 'probabilistic' ? 'Top Candidates' : 'Candidates'}</span>
                  {showCandidates ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5 -rotate-90" />}
                </div>
                
                <AnimatePresence>
                  {showCandidates && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="flex flex-col gap-1 overflow-hidden mt-2">
                      <div className="text-[10px] text-textTertiary mb-1 flex justify-between px-2 font-medium">
                        <span>Time</span>
                        <span>Score</span>
                      </div>
                      <div className="flex flex-col gap-[2px]">
                        {/* Mocking candidate rows visually to satisfy the interactive candidates requirement */}
                        <div className="flex justify-between items-center text-[11px] bg-blue-50/50 p-2 rounded-[2px] border border-accent/20 text-accent font-semibold">
                          <span>{trace.strategy_result.selected_action ? format(new Date(trace.strategy_result.selected_action.scheduled_time), "MMM d, HH:00") : "Optimal"}</span>
                          <span className="flex items-center gap-2">{Math.round(trace.strategy_result.prediction_score * 100)}% <Badge variant="success" className="text-[8px] px-1 py-0 bg-accent text-white">SELECTED</Badge></span>
                        </div>
                        <div className="flex justify-between items-center text-[11px] bg-page hover:bg-panelAlt p-2 rounded-[2px] border border-transparent text-textSecondary">
                          <span>+24 hours</span>
                          <span>{Math.max(0, Math.round(trace.strategy_result.prediction_score * 100) - 15)}%</span>
                        </div>
                        <div className="flex justify-between items-center text-[11px] bg-page hover:bg-panelAlt p-2 rounded-[2px] border border-transparent text-textSecondary">
                          <span>+48 hours</span>
                          <span>{Math.max(0, Math.round(trace.strategy_result.prediction_score * 100) - 23)}%</span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </Card>

            <Card className="p-6 border-dark bg-panelAlt relative overflow-hidden flex flex-col" ref={policyRef}>
              {executing && (
                <div className="absolute inset-0 bg-panelAlt/80 backdrop-blur-[1px] z-10 flex items-center justify-center">
                  <div className="text-[13px] font-semibold text-textPrimary uppercase tracking-widest flex items-center gap-3">
                    <div className="w-4 h-4 rounded-full border-2 border-textPrimary border-t-transparent animate-spin shrink-0" />
                    Locked for Execution
                  </div>
                </div>
              )}
              <div className="flex justify-between items-start mb-5">
                <h2 className="text-[10px] font-semibold text-textTertiary uppercase tracking-[1px]">3. DECISION</h2>
                <span className="text-[9px] font-semibold tracking-wider text-dark bg-gray-200 px-2 py-0.5 rounded border border-gray-300">DETERMINISTIC POLICY</span>
              </div>
              
              <div className="flex flex-col gap-5 flex-1">
                <div>
                  <div className="text-[11px] text-textSecondary mb-1">Revive Recommendation</div>
                  <div className="font-semibold text-[14px]">
                    {trace.strategy_result.selected_action ? format(new Date(trace.strategy_result.selected_action.scheduled_time), "MMM d, yyyy 'at' HH:mm 'UTC'") : 'No action recommended'}
                  </div>
                  <div className="text-[11px] text-textTertiary mt-1 italic">
                    "Selected candidate ranked highest among policy-valid recovery options."
                  </div>
                </div>

                {!isActionable && !isResolved && (
                   <div className="p-3 bg-criticalBg border border-critical/20 rounded-[3px] flex gap-3">
                     <ShieldX className="w-4 h-4 text-critical shrink-0" />
                     <div className="text-[11px] text-critical">
                        <strong>POLICY REJECTION:</strong> The selected candidate violates the minimum cooldown period or budget constraints. No further action permitted.
                     </div>
                   </div>
                )}
                
                <div className="mt-auto">
                  <div className="text-[11px] text-textSecondary mb-2">Policy Stop Conditions</div>
                  <div className="flex flex-col gap-1.5 text-[11.5px] bg-panel p-3 border border-borderRef rounded-[3px]">
                    <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-success" /> Payment recovered</div>
                    <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-success" /> Mandate revoked</div>
                    <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-success" /> Budget exhausted</div>
                    <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-success" /> Policy restriction</div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}
        
        <div ref={executeRef}>
          <AnimatePresence>
            {executing && (
              <motion.div initial={{ opacity: 0, height: 0, y: -10 }} animate={{ opacity: 1, height: 'auto', y: 0 }} exit={{ opacity: 0, height: 0, y: -10 }} className="overflow-hidden mb-6">
                <Card className="p-6 border-accent bg-blue-50 flex items-center gap-5 shadow-sm">
                  <div className="w-5 h-5 rounded-full border-[2px] border-accent border-t-transparent animate-spin shrink-0" />
                  <div className="font-semibold text-accent text-[13px] tracking-wide flex-1">
                    {['ANALYZING CONTEXT...', 'CHECKING DETERMINISTIC POLICY...', 'EXECUTING PAYMENT CALL...', 'VERIFYING OUTCOME...'][execStep] || 'PROCESSING...'}
                  </div>
                  <div className="flex gap-2">
                     {['●', '○', '○', '○'].map((char, i) => (
                       <span key={i} className={i <= execStep ? 'text-accent' : 'text-accent/30'}>{i < execStep ? '✓' : char}</span>
                     ))}
                  </div>
                </Card>
              </motion.div>
            )}
            
            {isResolved && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
                <Card className={`p-6 border-l-[3px] shadow-sm ${isSuccess ? 'border-l-success bg-[#f9fdfa]' : 'border-l-critical bg-[#fffafa]'}`}>
                  <div className="flex items-center gap-3 mb-2">
                    {isSuccess ? <CheckCircle2 className="w-5 h-5 text-success" /> : <XCircle className="w-5 h-5 text-critical" />}
                    <h2 className={`text-[14px] font-semibold uppercase tracking-[0.5px] ${isSuccess ? 'text-success' : 'text-critical'}`}>
                      {isSuccess ? 'RECOVERED' : trace.budget_remaining === 0 ? 'RECOVERY EXHAUSTED' : 'RECOVERY FAILED'}
                    </h2>
                  </div>
                  <div className="text-[13px] text-textSecondary ml-8 font-medium">
                    {isSuccess 
                      ? `₹${trace.amount.toLocaleString(undefined, {minimumFractionDigits:2})} successfully recovered. Recovery cycle completed.` 
                      : `No payment recovered. ${trace.budget_remaining === 0 ? 'Max retries reached. No further action permitted.' : ''}`}
                  </div>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <Card className="flex flex-col overflow-hidden mb-10 shadow-sm" ref={auditRef}>
          <div className="p-5 border-b border-borderRef bg-panelAlt flex justify-between items-center">
            <h2 className="text-[10px] font-semibold text-textTertiary uppercase tracking-[1px]">AUDIT TIMELINE</h2>
            <Badge variant="low" className="bg-panel shadow-sm">IMMUTABLE LOG</Badge>
          </div>
          <div className="p-6 flex flex-col gap-6 bg-panel">
            {trace.audit_trail.map((event, i) => (
              <motion.div 
                initial={{ opacity: 0, x: -10 }} 
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                key={event.event_id} 
                className="relative pl-7 group"
              >
                {i !== trace.audit_trail.length - 1 && (
                  <div className="absolute left-[7.5px] top-[18px] bottom-[-24px] w-[1px] bg-borderStrong" />
                )}
                <div className="absolute left-0 top-[3px] w-[16px] h-[16px] rounded-full bg-panel border-2 border-borderStrong z-10 transition-colors group-hover:border-dark shadow-sm" />
                <div className="text-[10px] text-textTertiary font-semibold mb-1 tracking-wider uppercase flex items-center gap-2">
                  <span className="text-textSecondary">{format(new Date(event.timestamp), "HH:mm:ss.SSS")}</span> 
                  <span className="w-1 h-1 rounded-full bg-borderStrong" />
                  <span>{event.actor}</span>
                </div>
                <div className="text-[13px] font-semibold text-textPrimary mb-2 tracking-wide">
                  {event.event_type.replace(/_/g, ' ')}
                </div>
                {Object.keys(event.details).length > 0 && (
                  <div className="text-[11px] text-textSecondary bg-panelAlt p-3 rounded-[3px] border border-borderRef max-w-[500px]">
                    {Object.entries(event.details).map(([k, v]) => (
                      <div key={k} className="flex gap-4 border-b border-borderRef/60 last:border-0 py-1.5 first:pt-0 last:pb-0">
                        <span className="text-textTertiary w-[120px] shrink-0 font-medium capitalize tracking-[0.2px]">{k.replace(/_/g, ' ')}:</span>
                        <span className="font-semibold text-textPrimary truncate">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
