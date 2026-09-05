with open('src/api/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_trigger = False
for line in lines:
    if line.startswith('def trigger_recovery'):
        in_trigger = True
    if in_trigger:
        print(line, end='')
