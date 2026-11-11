"""Update main.py in container"""
import subprocess
import sys

# Read the updated main.py
with open(r'C:\Users\Администратор\Desktop\Новая папка (2)\CareerAI\app\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Write to container using base64 encoding
import base64
encoded = base64.b64encode(content.encode('utf-8')).decode('ascii')

# Create a command to decode and write
cmd = f'docker exec career-ai python -c "import base64; Path(\'/app/app/main.py\').write_text(base64.b64decode(\'{encoded}\').decode(\'utf-8\'), encoding=\'utf-8\')"'

print(f'Running: {cmd[:100]}...')
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print('STDOUT:', result.stdout)
print('STDERR:', result.stderr)
print('RETURN CODE:', result.returncode)
