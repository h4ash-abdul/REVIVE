import re

with open('frontend/src/pages/CaseDetail.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('"MMM d Â· HH:mm"', '"MMM d HH:mm"')
c = c.replace('"Tomorrow Â· 09:00"', '"Tomorrow 09:00"')
c = c.replace('"Tomorrow · 09:00"', '"Tomorrow 09:00"')
c = c.replace('"MMM d · HH:mm"', '"MMM d HH:mm"')

# also replace the A if it was read differently
c = re.sub(r'"MMM d [^\"]+ HH:mm"', '"MMM d HH:mm"', c)
c = re.sub(r'"Tomorrow [^\"]+ 09:00"', '"Tomorrow 09:00"', c)

with open('frontend/src/pages/CaseDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
