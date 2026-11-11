#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

f = os.path.join('frontend', 'src', 'pages', 'admin', 'AdminUsers.tsx')
c = open(f, encoding='utf-8').read()

# Find the grid line
idx = c.find('grid grid-cols-2')
start = c.rfind('\n', 0, idx) + 1
end = c.find('\n', idx, len(c))
end = c.find('\n', end+1, len(c))
end = c.find('\n', end+1, len(c))
end = c.find('\n', end+1, len(c))
end = c.find('\n', end+1, len(c))
text = c[start:end]

# Build old1 from the file itself
old1 = text

# Build new1
new1 = '        <div className="space-y-4">\n          <div>\n            <label className="block text-sm font-medium text-slate-600 mb-1">Логин</label>\n            <input value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}\n              className="w-full p-2 border rounded-lg" />\n          </div>\n          <div>\n            <label className="block text-sm font-medium text-slate-600 mb-1">Пароль</label>\n            <input type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}\n              className="w-full p-2 border rounded-lg" />\n          </div>\n        </div>'

c = c.replace(old1, new1)
print("Replaced:", old1 in new1 == False and "yes" or "no")  # hacky check
print("Text in content still:", old1 in c)

open(f, 'w', encoding='utf-8', newline='').write(c)
print("Done")

