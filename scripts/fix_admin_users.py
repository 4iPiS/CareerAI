#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

f = os.path.join('frontend', 'src', 'pages', 'admin', 'AdminUsers.tsx')
content = open(f, encoding='utf-8').read()

# Debug: show exact text around "grid grid-cols-2"
idx = content.find('grid grid-cols-2')
if idx >= 0:
    print("Found 'grid grid-cols-2' at char:", idx)
    print("Surrounding text:")
    print(repr(content[idx-30:idx+300]))
else:
    print("grid grid-cols-2 NOT FOUND")


