import os

with open('write_app_layout.py', 'r', encoding='utf-8') as f:
    c = f.read()
with open('write_app_layout.py', 'w', encoding='utf-8') as f:
    f.write(c)
