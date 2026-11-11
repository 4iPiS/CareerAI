with open('templates/index.html', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
for term in ['token', 'bearer', 'authorization', 'admin_token', 'localStorage', 'cookie', 'Authorization']:
    idx = content.lower().find(term.lower())
    if idx >= 0:
        start = max(0, content.rfind('\n', 0, idx-100))
        end = content.find('\n', idx, idx+200)
        print(f'--- Found "{term}" ---')
        print(content[start:end][:300])
        print()