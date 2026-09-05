import re
with open('frontend/src/pages/Workspace.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('minimumFractionDigits: 0', 'maximumFractionDigits: 0')

with open('frontend/src/pages/Workspace.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
