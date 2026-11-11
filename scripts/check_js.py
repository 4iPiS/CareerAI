import os

# Read JS from container
cmd = "docker exec career-ai python -c \"import sys; f=open('/app/static/assets/index-CXSJlvGa.js','rb'); c=f.read(); print(b'urvey:', b'urvey' in c); print(b'submitAnswer:', b'submitAnswer' in c); print(b'/answer:', b'/answer' in c); print(b'/survey:', b'/survey' in c); print(b'survey:', b'survey' in c); print(b'size:', len(c))\""
result = os.popen(cmd + ' 2>&1').read()
print(result)
