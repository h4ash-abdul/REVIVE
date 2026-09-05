import re
with open('frontend/src/types/index.ts', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('outcome: VerificationOutcome | null;', 'outcome: VerificationOutcome | null;\n  last_attempt_outcome?: VerificationOutcome | null;')

with open('frontend/src/types/index.ts', 'w', encoding='utf-8') as f:
    f.write(c)
