import re

with open('frontend/src/App.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

if "import Architecture" not in c:
    c = c.replace("import Evidence from './pages/Evidence'", "import Evidence from './pages/Evidence'\nimport Architecture from './pages/Architecture'")
    c = c.replace("<Route path=\"/evidence\" element={<Evidence />} />", "<Route path=\"/evidence\" element={<Evidence />} />\n        <Route path=\"/architecture\" element={<Architecture />} />")
    with open('frontend/src/App.tsx', 'w', encoding='utf-8') as f:
        f.write(c)

with open('frontend/src/pages/Architecture.tsx', 'w', encoding='utf-8') as f:
    f.write('''import { motion } from 'framer-motion'

export default function Architecture() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-10 max-w-[1000px] w-full">
      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-semibold text-[#1f2023] tracking-tight">System Architecture</h1>
        <p className="text-[14px] text-[#6b6d7c] max-w-[600px] leading-relaxed">
          The REVIVE engine operates a controlled loop of intelligence bounded by deterministic policy.
        </p>
      </div>
      
      <div className="bg-white p-10 border border-[#e5e7eb] rounded-lg shadow-sm flex flex-col items-center">
        {/* Placeholder for the diagram */}
      </div>
    </motion.div>
  )
}
''')
