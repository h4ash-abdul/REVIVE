import { motion } from 'framer-motion'
import { ArrowDown, BrainCircuit, ShieldCheck, Cog, Activity } from 'lucide-react'

const Stage = ({ title, type, desc, delay }: any) => {
  const getTypeProps = () => {
    switch(type) {
      case 'AI': return { icon: BrainCircuit, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20', label: 'PROBABILISTIC' };
      case 'Policy': return { icon: ShieldCheck, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', label: 'DETERMINISTIC' };
      case 'System': return { icon: Cog, color: 'text-gray-400', bg: 'bg-gray-700/30', border: 'border-gray-600/30', label: 'CONTROLLED SYSTEM' };
      default: return { icon: Activity, color: 'text-gray-400', bg: 'bg-gray-700/30', border: 'border-gray-600/30', label: '' };
    }
  }
  const t = getTypeProps();
  const Icon = t.icon;
  
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }} className="flex flex-col items-center">
      <div className={`w-[450px] p-5 rounded border ${t.border} bg-[#16171a] flex items-center justify-between`}>
        <div className="flex flex-col gap-1.5">
          <span className="text-[11px] font-bold text-white tracking-widest uppercase">{title}</span>
          <span className="text-[9px] font-mono text-gray-400 uppercase tracking-wider">{desc}</span>
        </div>
        <div className={`px-2 py-1 rounded flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest border ${t.bg} ${t.color} ${t.border}`}>
          <Icon className="w-3.5 h-3.5" />
          {t.label}
        </div>
      </div>
    </motion.div>
  )
}

const Arrow = ({ delay }: any) => (
  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay }} className="h-8 flex items-center justify-center">
    <ArrowDown className="w-4 h-4 text-gray-600" />
  </motion.div>
)

export default function Architecture() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[1400px] w-full mx-auto pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-bold text-white tracking-widest uppercase">SYSTEM ARCHITECTURE</h1>
        <p className="text-[11px] text-gray-500 font-bold tracking-widest uppercase mb-4 max-w-[700px]">
          The REVIVE engine operates a controlled loop of intelligence bounded by deterministic policy. AI predictions NEVER execute without explicit, rules-based authorization.
        </p>
      </div>
      
      <div className="flex flex-col items-center mt-2">
        <Stage title="FAILED PAYMENT" type="System" desc="Ingestion of network failure codes and context" delay={0.1} />
        <Arrow delay={0.2} />
        <Stage title="CLASSIFY" type="System" desc="Rule-based classification of failure category" delay={0.3} />
        <Arrow delay={0.4} />
        <Stage title="POINT-IN-TIME FEATURES" type="System" desc="Historical behavior and temporal context construction" delay={0.5} />
        <Arrow delay={0.6} />
        <Stage title="CANDIDATES" type="System" desc="Generation of possible future recovery execution slots" delay={0.7} />
        <Arrow delay={0.8} />
        <Stage title="DETERMINISTIC POLICY (Pre-filter)" type="Policy" desc="Pruning of candidates violating cooldowns or budgets" delay={0.9} />
        <Arrow delay={1.0} />
        <Stage title="RECOVERY PREDICTION" type="AI" desc="Hierarchical LightGBM scoring of surviving candidates" delay={1.1} />
        <Arrow delay={1.2} />
        <Stage title="DETERMINISTIC POLICY (Auth)" type="Policy" desc="Final authorization of highest-EV candidate" delay={1.3} />
        <Arrow delay={1.4} />
        <Stage title="EXECUTION" type="System" desc="Dispatching the network retry call" delay={1.5} />
        <Arrow delay={1.6} />
        <Stage title="VERIFICATION" type="System" desc="Reconciliation of payment outcome" delay={1.7} />
        <Arrow delay={1.8} />
        <Stage title="AUDIT" type="System" desc="Immutable logging of all decisions and scores" delay={1.9} />
      </div>
    </motion.div>
  )
}
