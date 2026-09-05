import re
with open('src/api/main.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('from src.simulation.outcome_engine.engine import OutcomeEngine\n', '')
c = c.replace('outcome_engine = OutcomeEngine(random.Random(42))\n', '')
c = c.replace('adapter = SimulatedExecutionAdapter(outcome_engine)\n', '')

with open('src/api/main.py', 'w', encoding='utf-8') as f:
    f.write(c)
