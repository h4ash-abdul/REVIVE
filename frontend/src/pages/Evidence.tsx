import { motion } from 'framer-motion'
import { CheckCircle2, TrendingUp, BarChart2 } from 'lucide-react'

export default function Evidence() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[1400px] w-full mx-auto pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-bold text-white tracking-widest uppercase">SYSTEM EVIDENCE</h1>
        <p className="text-[11px] text-gray-500 font-bold tracking-widest uppercase mb-4">
          Simulated synthetic evaluation proving incremental business value.
        </p>
      </div>

      <div className="flex flex-col gap-8 mt-4">
        {/* RECOVERY VALUE */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 border-b border-[#222328] pb-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">RECOVERY VALUE</h2>
          </div>
          <div className="p-0 overflow-hidden border border-[#222328] bg-[#16171a] rounded">
            <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[#222328]">
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">NO RECOVERY BASELINE</span>
                <span className="text-[24px] font-mono font-bold text-white">₹0</span>
              </div>
              <div className="p-6 flex flex-col gap-2 bg-[#1e1f24]/50">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">REVIVE YIELD</span>
                <span className="text-[24px] font-mono font-bold text-emerald-400">₹50,192<span className="text-[14px] font-normal text-emerald-400/50">.12</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">RECOVERY RATE</span>
                <span className="text-[24px] font-mono font-bold text-white">39.3%</span>
              </div>
            </div>
          </div>
        </div>

        {/* DECISION BENCHMARK */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 border-b border-[#222328] pb-2">
            <BarChart2 className="w-4 h-4 text-gray-300" />
            <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">DECISION BENCHMARK (PHASE 13A)</h2>
          </div>
          <div className="p-0 overflow-hidden border border-[#222328] bg-[#16171a] rounded">
            <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[#222328]">
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">SMART HISTORICAL HEURISTIC</span>
                <span className="text-[24px] font-mono font-bold text-white">₹50,192<span className="text-[14px] font-normal text-gray-600">.12</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">CALIBRATED ML</span>
                <span className="text-[24px] font-mono font-bold text-white">₹50,192<span className="text-[14px] font-normal text-gray-600">.12</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2 bg-[#1e1f24]/50">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">INCREMENTAL LIFT</span>
                <span className="text-[24px] font-mono font-bold text-gray-400">0.00%</span>
              </div>
            </div>
            <div className="p-4 border-t border-[#222328] bg-[#121316] text-[11px] font-mono text-gray-500 leading-relaxed uppercase tracking-wider">
              ML PERFECTLY MATCHES HEURISTIC IN HIGH-SIGNAL ENVIRONMENTS, PROVIDING A SAFE BASELINE FOR EXPERIMENTATION.
            </div>
          </div>
        </div>

        {/* ECONOMIC PRIORITIZATION */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 border-b border-[#222328] pb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">ECONOMIC PRIORITIZATION (PHASE 13B)</h2>
          </div>
          <div className="p-0 overflow-hidden border border-[#222328] bg-[#16171a] rounded">
            <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[#222328]">
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">PROBABILITY RANKING</span>
                <span className="text-[24px] font-mono font-bold text-white">₹18,400<span className="text-[14px] font-normal text-gray-600">.37</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2 bg-[#1e1f24]/50">
                <span className="text-[10px] text-emerald-500 font-bold uppercase tracking-widest">EXPECTED VALUE RANKING</span>
                <span className="text-[24px] font-mono font-bold text-white">₹21,422<span className="text-[14px] font-normal text-gray-600">.74</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2 bg-emerald-500/10">
                <span className="text-[10px] text-emerald-500 font-bold uppercase tracking-widest">EV UPLIFT</span>
                <span className="text-[24px] font-mono font-bold text-emerald-400">+16.43%</span>
              </div>
            </div>
            <div className="p-4 border-t border-[#222328] bg-[#121316] text-[11px] font-mono text-gray-500 leading-relaxed uppercase tracking-wider">
              EXPECTED VALUE (EV) SORTING GENERATES 16.43% MORE REVENUE THAN RAW PROBABILITY SORTING WHEN EXECUTION CONSTRAINED.
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
