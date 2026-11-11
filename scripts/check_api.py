import urllib.request
import json

# Test /api/v1/start
req = urllib.request.Request('http://localhost:7777/api/v1/start', method='POST')
try:
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())
    print('POST /api/v1/start:', resp.status)
    print('session_id:', data.get('session_id', 'MISSING'))
    print('question is_custom:', data.get('question', {}).get('is_custom', 'MISSING'))
    print('progress:', json.dumps(data.get('progress', {}), indent=2)[:500])
except urllib.error.HTTPError as e:
    print('POST /api/v1/start FAILED:', e.code)
    print('Body:', e.read().decode()[:500])
except Exception as e:
    print('POST /api/v1/start ERROR:', e)

print('---')

# Test /api/v1/settings
try:
    resp = urllib.request.urlopen('http://localhost:7777/api/v1/settings', timeout=5)
    data = json.loads(resp.read().decode())
    print('GET /api/v1/settings:', resp.status)
    print('settings:', json.dumps(data.get('settings', {}), indent=2)[:500])
except Exception as e:
    print('GET /api/v1/settings ERROR:', e)

print('---')

# Test directions
try:
    resp = urllib.request.urlopen('http://localhost:7777/api/v1/directions', timeout=5)
    data = json.loads(resp.read().decode())
    print('GET /api/v1/directions:', resp.status, 'count:', len(data.get('directions', [])))
except Exception as e:
    print('GET /api/v1/directions ERROR:', e)
