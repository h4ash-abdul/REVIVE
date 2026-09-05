import re

with open('src/api/main.py', 'r', encoding='utf-8') as f:
    c = f.read()

find_str = '''    # Return as dict to inject obligation status
    res = trace_obj.model_dump()
    res["obligation_status"] = t["obligation"].status.value
    return res'''

replace_str = '''    # Return as dict to inject obligation status
    res = trace_obj.model_dump()
    res["obligation_status"] = t["obligation"].status.value
    res["initial_probability"] = DEMO_CASES[key].get("initial_probability", 0.0)
    return res'''

c = c.replace(find_str, replace_str)

with open('src/api/main.py', 'w', encoding='utf-8') as f:
    f.write(c)
