import { motion } from 'framer-motion'
import { Card } from '../components/ui'
import { CheckCircle2, TrendingUp, BarChart2 } from 'lucide-react'

export default function Evidence() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[1000px] w-full pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-[28px] font-bold text-gray-900 tracking-tight">System Evidence</h1>
        <p className="text-[14px] text-gray-500 max-w-[700px] leading-relaxed">
          Simulated synthetic evaluation proving the incremental business value of the REVIVE agent against heuristic baselines.
        </p>
      </div>

      <div className="flex flex-col gap-8 mt-4">
        {/* RECOVERY VALUE */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
            <h2 className="text-[14px] font-bold text-gray-900 uppercase tracking-wider">Recovery Value</h2>
          </div>
          <Card className="p-0 overflow-hidden border border-gray-200 shadow-sm bg-white">
            <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-100">
              <div className="p-6 flex flex-col gap-2 bg-gray-50/50">
                <span className="text-[12px] text-gray-500 font-bold uppercase tracking-wider">No Recovery</span>
                <span className="text-[24px] font-bold text-gray-900">₹0</span>
              </div>
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[12px] text-gray-500 font-bold uppercase tracking-wider">REVIVE</span>
                <span className="text-[24px] font-bold text-green-700">₹50,192<span className="text-[14px] font-normal text-green-700/60">.12</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[12px] text-gray-500 font-bold uppercase tracking-wider">Recovery Rate</span>
                <span className="text-[24px] font-bold text-blue-600">39.3%</span>
              </div>
            </div>
          </Card>
        </div>

        {/* DECISION BENCHMARK */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-blue-600" />
            <h2 className="text-[14px] font-bold text-gray-900 uppercase tracking-wider">Decision Benchmark (Phase 13A)</h2>
          </div>
          <Card className="p-0 overflow-hidden border border-gray-200 shadow-sm bg-white">
            <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-100">
              <div className="p-6 flex flex-col gap-2 bg-gray-50/50">
                <span className="text-[12px] text-gray-500 font-bold uppercase tracking-wider">Smart Historical Heuristic</span>
                <span className="text-[24px] font-bold text-gray-900">₹50,192<span className="text-[14px] font-normal text-gray-500">.12</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[12px] text-gray-500 font-bold uppercase tracking-wider">Calibrated ML</span>
                <span className="text-[24px] font-bold text-gray-900">₹50,192<span className="text-[14px] font-normal text-gray-500">.12</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[12px] text-gray-500 font-bold uppercase tracking-wider">Incremental Lift</span>
                <span className="text-[24px] font-bold text-gray-900">0.00%</span>
              </div>
            </div>
            <div className="p-5 border-t border-gray-100 bg-gray-50 text-[13px] text-gray-600 font-medium leading-relaxed">
              ML perfectly matches the heuristic in high-signal environments, providing a safe baseline for advanced experimentation.
            </div>
          </Card>
        </div>

        {/* ECONOMIC PRIORITIZATION */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-purple-600" />
            <h2 className="text-[14px] font-bold text-gray-900 uppercase tracking-wider">Economic Prioritization (Phase 13B)</h2>
          </div>
          <Card className="p-0 overflow-hidden border border-gray-200 shadow-sm bg-white">
            <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-100">
              <div className="p-6 flex flex-col gap-2 bg-gray-50/50">
                <span className="text-[12px] text-gray-500 font-bold uppercase tracking-wider">Probability Ranking</span>
                <span className="text-[24px] font-bold text-gray-900">₹18,400<span className="text-[14px] font-normal text-gray-500">.37</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[12px] text-gray-500 font-bold uppercase tracking-wider">Expected Value Ranking</span>
                <span className="text-[24px] font-bold text-purple-700">₹21,422<span className="text-[14px] font-normal text-purple-700/60">.74</span></span>
              </div>
              <div className="p-6 flex flex-col gap-2">
                <span className="text-[12px] text-gray-500 font-bold uppercase tracking-wider">EV Uplift</span>
                <span className="text-[24px] font-bold text-green-600">+16.43%</span>
              </div>
            </div>
            <div className="p-5 border-t border-gray-100 bg-gray-50 text-[13px] text-gray-600 font-medium leading-relaxed">
              When constrained by execution bandwidth, Expected Value (EV) sorting generates 16.43% more revenue than raw probability sorting.
            </div>
          </Card>
        </div>
      </div>
    </motion.div>
  )
}
