import httpx
import json

url = "http://host.docker.internal:1234/v1/chat/completions"
payload = {
    "model": "qwen2.5-1.5b-v1-3b-ins",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 20
}

try:
    r = httpx.post(url, json=payload, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
