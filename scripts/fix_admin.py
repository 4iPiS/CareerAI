import re

# === 1. Fix AdminDashboard.tsx ===
path = 'frontend/src/pages/admin/AdminDashboard.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix statCards array - add back missing cards without emoji
old_stat = """    const statCards: StatCard[] = [
        { label: 'Всего сессий', value: stats?.total ?? 0 },
    ]"""
new_stat = """    const statCards = [
        { label: 'Всего сессий', value: stats?.total ?? 0 },
        { label: 'Завершено', value: stats?.completed ?? 0 },
        { label: 'В процессе', value: stats?.in_progress ?? 0 },
        { label: 'С профилем', value: stats?.with_profile ?? 0 },
        { label: 'С метками', value: stats?.labeled ?? 0 },
    ]"""
content = content.replace(old_stat, new_stat)

# Remove the icon display from stat card rendering
old_card = """<div key={card.label} className="bg-white rounded-xl p-5 shadow-sm text-center">
                        <div className="text-2xl mb-1">{card.icon}</div>
                        <div className="text-2xl font-bold text-slate-800">{formatNumber(card.value)}</div>"""
new_card = """<div key={card.label} className="bg-white rounded-xl p-5 shadow-sm text-center">
                        <div className="text-2xl font-bold text-slate-800">{formatNumber(card.value)}</div>"""
content = content.replace(old_card, new_card)

# Remove interface StatCard with icon
content = content.replace(
    "interface StatCard {\n    label: string\n    value: number\n    icon: string\n}",
    "interface StatCard {\n    label: string\n    value: number\n}"
)

# Remove emoji from all button texts
content = content.replace('\U0001F504 \u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c', '\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c')
content = content.replace('\u2139\uFE0F \u041f\u0440\u0438 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0438\u0438', '\u041f\u0440\u0438 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0438\u0438')
content = content.replace('\U0001F4E5 \u042d\u043a\u0441\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0438\u0437 \u0411\u0414', '\u042d\u043a\u0441\u043f\u043e\u0440\u0442\u0438\u0440\u0432\u0430\u0442\u044c \u0438\u0437 \u0411\u0414')
content = content.replace('\u2B06 \u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c CSV', '\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c CSV')
content = content.replace('\U0001F6E0 \u0421\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0438\u043d\u0442\u0435\u0442\u0438\u0447\u0435\u0441\u043a\u0443\u044e', '\u0421\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0438\u043d\u0442\u0435\u0442\u0438\u0447\u0435\u0441\u043a\u0443\u044e')
content = content.replace('\u2B07 \u0421\u043a\u0430\u0447\u0430\u0442\u044c CSV', '\u0421\u043a\u0430\u0447\u0430\u0442\u044c CSV')
content = content.replace('\u23F2 \u041e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c', '\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("AdminDashboard.tsx fixed")

# === 2. Fix AdminResponses.tsx ===
path = 'frontend/src/pages/admin/AdminResponses.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('\U0001F4E5 \u042d\u043a\u0441\u043f\u043e\u0440\u0442 CSV', '\u042d\u043a\u0441\u043f\u043e\u0440\u0442 CSV')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("AdminResponses.tsx fixed")

# === 3. Fix admin.js - remove emoji ===
path = 'app/admin_ui/static/admin.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all emoji in admin.js with empty string or neutral text
# These are the specific emoji patterns found in admin.js
replacements = [
    ('\U0001F509 ', ''),  # 🔉
    ('\u2139\uFE0F ', ''),  # ℹ️
    ('\U0001F4E5 ', ''),  # 📥
    ('\u2B06 ', ''),  # ⬆
    ('\U0001F6E0 ', ''),  # 🛠
    ('\u2B07 ', ''),  # ⬇
    ('\u270E', '✏'),  # ✎ -> pencil text
    ('\U0001F5D1', ''),  # 🗑
    ('\u2317', ''),  # ⎈
    ('\u2714', ''),  # ✔
    ('\u274C', ''),  # ❌
    ('\u23F2', ''),  # ⏲
    ('\u2B05', ''),  # ⬅
    ('\u2794', ''),  # ➔
    ('\u21BB', ''),  # ↻
    ('\u25AB', ''),  # ▫
    ('\u25AA', ''),  # ▪
]
for old, new in replacements:
    content = content.replace(old, new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("admin.js fixed")

# === 4. Fix templates/index.html ===
path = 'templates/index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('\u274C \u041e\u0448\u0438\u0431\u043a\u0430', '\u041e\u0448\u0438\u0431\u043a\u0430')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html fixed")

print("\nAll emoji removal done!")
