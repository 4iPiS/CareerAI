import urllib.request
import json

BASE = 'http://localhost:7777'

# 1. Start survey
req = urllib.request.Request(f'{BASE}/api/v1/start', method='POST')
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read().decode())
print('=== POST /api/v1/start ===')
print('session_id:', data.get('session_id'))
q = data.get('question', {})
print('question.id:', q.get('id'))
print('question.is_custom:', q.get('is_custom'))
print('question.fields count:', len(q.get('fields', [])))
print('question.consent_text present:', 'consent_text' in q)
print('question.progress:', q.get('progress'))
print('top-level progress:', data.get('progress'))

session_id = data.get('session_id')

# 2. Submit custom form data via /api/v1/survey-data
custom_data = {
    'full_name': 'Тест Тестов',
    'phone': '+79001234567',
    'email': 'test@example.com',
}
payload = json.dumps({'session_id': session_id, 'data': custom_data, 'consent': True}).encode()
req2 = urllib.request.Request(f'{BASE}/api/v1/survey-data', data=payload, method='POST')
req2.add_header('Content-Type', 'application/json')
try:
    resp2 = urllib.request.urlopen(req2, timeout=30)
    data2 = json.loads(resp2.read().decode())
    print('\n=== POST /api/v1/survey-data ===')
    print('HTTP:', resp2.status)
    print('done:', data2.get('done'))
    q2 = data2.get('question', {})
    if q2:
        print('next question.id:', q2.get('id'))
        print('next question.is_custom:', q2.get('is_custom'))
        print('next question.type:', q2.get('type'))
        print('next question.progress:', q2.get('progress'))
    else:
        print('No next question')
except urllib.error.HTTPError as e:
    print('\n=== POST /api/v1/survey-data FAILED ===')
    print('HTTP:', e.code)
    print('Body:', e.read().decode()[:300])
