import re
with open('src/api/main.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('res["initial_probability"] = DEMO_CASES[key].get("initial_probability", 0.0)', 'res["initial_probability"] = DEMO_CASES[key].get("initial_probability", 0.0)\n    res["last_attempt_outcome"] = trace_obj.outcome.model_dump() if trace_obj.outcome else None')

with open('src/api/main.py', 'w', encoding='utf-8') as f:
    f.write(c)
