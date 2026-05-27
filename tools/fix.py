with open('voice_cover.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('[i]\"\"', '[i]\"')
with open('voice_cover.py', 'w', encoding='utf-8') as f:
    f.write(c)
