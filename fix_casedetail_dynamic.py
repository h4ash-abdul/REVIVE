import re

with open('frontend/src/pages/CaseDetail.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace hardcoded 72% with dynamic
c = c.replace(
    '''<span className="text-[32px] font-bold text-gray-900 leading-none">72<span className="text-[16px] text-gray-400">%</span></span>''',
    '''<span className="text-[32px] font-bold text-gray-900 leading-none">{trace.initial_probability ? (trace.initial_probability * 100).toFixed(0) : 72}<span className="text-[16px] text-gray-400">%</span></span>'''
)

# And strokeDashoffset for circle
c = c.replace(
    '''strokeDashoffset={351.8 - (351.8 * 0.72)}''',
    '''strokeDashoffset={351.8 - (351.8 * (trace.initial_probability || 0.72))}'''
)

# And replace hardcoded "Tomorrow 09:00" in Decision Panel
c = c.replace(
    '''Retry Tomorrow · 09:00''',
    '''Retry {trace.strategy_result?.selected_action ? format(new Date(trace.strategy_result.selected_action.timestamp), "MMM d · HH:mm") : "Tomorrow · 09:00"}'''
)

# Also fix the candidates table hardcoded 72
c = c.replace(
    '''<td className="px-4 py-3 text-blue-600 font-bold">72%</td>''',
    '''<td className="px-4 py-3 text-blue-600 font-bold">{trace.initial_probability ? (trace.initial_probability * 100).toFixed(0) : 72}%</td>'''
)

# And candidate time
c = c.replace(
    '''<td className="px-4 py-3 text-gray-900 font-bold">Tomorrow · 09:00</td>''',
    '''<td className="px-4 py-3 text-gray-900 font-bold">{trace.strategy_result?.selected_action ? format(new Date(trace.strategy_result.selected_action.timestamp), "MMM d · HH:mm") : "Tomorrow · 09:00"}</td>'''
)


with open('frontend/src/pages/CaseDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
