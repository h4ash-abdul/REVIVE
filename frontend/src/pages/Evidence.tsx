import { motion } from 'framer-motion'
import { Card } from '../components/ui'

export default function Evidence() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[900px]">
      <div>
        <h1 className="text-[22px] font-semibold m-0 text-textPrimary">Evaluation Evidence</h1>
        <p className="text-[12.5px] text-textSecondary m-0 mt-1 max-w-[600px] leading-relaxed">
          Synthetic benchmark results establishing the financial validity and optimization characteristics of the REVIVE recovery strategies.
        </p>
      </div>

      <div className="flex flex-col gap-6">
        <h2 className="text-[14px] font-semibold text-textPrimary uppercase tracking-[0.5px]">Authoritative Benchmark</h2>
        <Card className="p-0 overflow-hidden border-borderRef">
          <div className="grid grid-cols-3 border-b border-borderRef bg-panelAlt">
            <div className="px-6 py-4 border-r border-borderRef">
              <div className="text-[11px] font-semibold text-textTertiary uppercase tracking-[0.5px] mb-2">Smart Historical Heuristic</div>
              <div className="text-[20px] font-semibold">₹50,192.12</div>
            </div>
            <div className="px-6 py-4 border-r border-borderRef">
              <div className="text-[11px] font-semibold text-textTertiary uppercase tracking-[0.5px] mb-2">Calibrated ML Policy</div>
              <div className="text-[20px] font-semibold text-accent">₹50,192.12</div>
            </div>
            <div className="px-6 py-4">
              <div className="text-[11px] font-semibold text-textTertiary uppercase tracking-[0.5px] mb-2">Incremental Lift</div>
              <div className="text-[20px] font-semibold">0.00%</div>
            </div>
          </div>
          <div className="px-6 py-4 text-[12px] text-textSecondary">
            The calibrated ML policy reproduced the strong historical heuristic on the locked synthetic benchmark, achieving exact strategic parity without degradation.
          </div>
        </Card>
      </div>

      <div className="flex flex-col gap-6">
        <h2 className="text-[14px] font-semibold text-textPrimary uppercase tracking-[0.5px]">Economic Prioritization</h2>
        <Card className="p-0 overflow-hidden border-borderRef">
          <div className="grid grid-cols-3 border-b border-borderRef bg-panelAlt">
            <div className="px-6 py-4 border-r border-borderRef">
              <div className="text-[11px] font-semibold text-textTertiary uppercase tracking-[0.5px] mb-2">Probability-based Prioritization</div>
              <div className="text-[20px] font-semibold">₹18,400.37</div>
            </div>
            <div className="px-6 py-4 border-r border-borderRef">
              <div className="text-[11px] font-semibold text-textTertiary uppercase tracking-[0.5px] mb-2">EV-based Prioritization</div>
              <div className="text-[20px] font-semibold text-success">₹21,422.74</div>
            </div>
            <div className="px-6 py-4">
              <div className="text-[11px] font-semibold text-textTertiary uppercase tracking-[0.5px] mb-2">EV Improvement</div>
              <div className="text-[20px] font-semibold text-success">16.43%</div>
            </div>
          </div>
          <div className="px-6 py-4 text-[12px] text-textSecondary">
            When recovery capacity is limited across mandates, expected-value prioritization recovered 16.43% more monetary value than probability ranking in the synthetic capacity experiment.
          </div>
        </Card>
      </div>
      
      <div className="text-[11px] text-textTertiary italic">
        * Note: All values are derived from synthetic environments. Do not imply either result is production performance.
      </div>
    </motion.div>
  )
}
