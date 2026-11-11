with open('app/models/survey.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add List import
if 'from typing import List' not in content:
    content = content.replace(
        'from typing import Optional',
        'from typing import List, Optional'
    )
    print('Added List import')

# Fix Mapped[list[...]] patterns for Python 3.8 compat
content = content.replace("Mapped[list['Question']]", "Mapped[List['Question']]")
content = content.replace('Mapped[list]', 'Mapped[List]')

with open('app/models/survey.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('survey.py fixed')
