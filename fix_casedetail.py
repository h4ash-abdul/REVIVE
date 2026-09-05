import re
with open('frontend/src/pages/CaseDetail.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace(
    "{isResolved && (",
    "{(isResolved || trace.last_attempt_outcome) && ("
)

c = c.replace(
    "isSuccess ? 'RECOVERY SUCCESSFUL' : trace.budget_remaining === 0 ? 'RECOVERY EXHAUSTED' : 'RECOVERY FAILED'",
    "isSuccess ? 'RECOVERY SUCCESSFUL' : trace.budget_remaining === 0 ? 'RECOVERY EXHAUSTED' : isResolved ? 'RECOVERY FAILED' : 'RECOVERY FAILED — RETRY AVAILABLE'"
)

with open('frontend/src/pages/CaseDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
