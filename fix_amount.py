import re
with open('frontend/src/pages/CaseDetail.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('minimumFractionDigits:0', 'minimumFractionDigits:0, maximumFractionDigits:0')

with open('frontend/src/pages/CaseDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
