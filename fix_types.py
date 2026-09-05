import re

with open('frontend/src/types/index.ts', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace("obligation_status: string;", "obligation_status: string;\n  initial_probability?: number;")

with open('frontend/src/types/index.ts', 'w', encoding='utf-8') as f:
    f.write(c)
