import re

with open('frontend/src/components/layout/AppLayout.tsx', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace("import { Activity, LayoutDashboard", "import { LayoutDashboard")
with open('frontend/src/components/layout/AppLayout.tsx', 'w', encoding='utf-8') as f:
    f.write(c)

with open('frontend/src/pages/CaseDetail.tsx', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace("Ban, ShieldX, ChevronDown", "Ban, ChevronDown")
with open('frontend/src/pages/CaseDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(c)

with open('frontend/src/pages/Evidence.tsx', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace("import { Card, Badge }", "import { Card }")
with open('frontend/src/pages/Evidence.tsx', 'w', encoding='utf-8') as f:
    f.write(c)

with open('frontend/src/types/index.ts', 'r', encoding='utf-8') as f:
    c = f.read()
if "recovered_amount?: number;" not in c:
    c = c.replace("initial_probability?: number;", "initial_probability?: number;\n  recovered_amount?: number;")
    with open('frontend/src/types/index.ts', 'w', encoding='utf-8') as f:
        f.write(c)

