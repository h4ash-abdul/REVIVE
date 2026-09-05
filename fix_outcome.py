import re

with open('frontend/src/pages/CaseDetail.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('trace.outcome?.success', "trace.outcome?.status === 'success'")
c = c.replace('trace.outcome?.network_return_code', "trace.outcome?.metadata?.network_return_code")

with open('frontend/src/pages/CaseDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
