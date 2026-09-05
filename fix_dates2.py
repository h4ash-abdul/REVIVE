import re

for filename in ['frontend/src/pages/Workspace.tsx', 'frontend/src/pages/Overview.tsx']:
    with open(filename, 'r', encoding='utf-8') as f:
        c = f.read()

    c = re.sub(r'Tomorrow [^\"]+ 09:00', 'Tomorrow 09:00', c)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(c)

