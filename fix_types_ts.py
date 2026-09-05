import re
with open('frontend/src/types/index.ts', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('outcome?: any;', 'outcome?: any;\n  last_attempt_outcome?: any;')

with open('frontend/src/types/index.ts', 'w', encoding='utf-8') as f:
    f.write(c)
