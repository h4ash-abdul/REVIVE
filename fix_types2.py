import re
with open('frontend/src/pages/CaseDetail.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('chartData.map(((d: any, i: number) =>', 'chartData.map((d: any, i: number) =>')

with open('frontend/src/pages/CaseDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
