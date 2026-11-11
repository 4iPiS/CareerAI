"""Test complete survey flow + admin API."""
import urllib.request
import json
import http.cookiejar

BASE = "http://localhost:7777"
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        r = opener.open(req, timeout=10)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read()
        parsed = json.loads(body) if body else {}
        return e.code, parsed

def get(path):
    req = urllib.request.Request(BASE + path)
    try:
        r = opener.open(req, timeout=5)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read()
        parsed = json.loads(body) if body else {}
        return e.code, parsed

print("=== API Health ===")
status, data = get("/health")
print(f"GET /health -> {status}: {data}")

print("\n=== Public API ===")
status, data = get("/api/v1/directions")
dirs = data.get("directions", [])
print(f"GET /api/v1/directions -> {status}: {len(dirs)} directions")

status, data = get("/api/v1/settings")
s = data.get("settings", {})
print(f"GET /api/v1/settings -> {status}")
print(f"  university_name: {s.get('university_name')}")
print(f"  contact_email: '{s.get('contact_email')}'")
print(f"  support_phone: '{s.get('support_phone')}'")

print("\n=== Survey Flow ===")
# Start
status, data = post("/api/v1/start", {})
session_id = data.get("session_id")
q = data.get("question", {})
print(f"POST /api/v1/start -> {status}")
print(f"  session_id: {session_id}")
print(f"  first question type: {q.get('type')}")

# Submit form data (custom questionnaire at start)
status, data = post("/api/v1/survey-data", {
    "session_id": session_id,
    "consent": True,
    "data": {"full_name": "Test User", "phone": "+79001234567", "email": "test@example.com"},
})
print(f"\nPOST /api/v1/survey-data -> {status}")
q = data.get("question", {})
print(f"  done: {data.get('done')}")
print(f"  next question type: {q.get('type')}")

# Answer rating questions iteratively
answered = 0
while answered < 15 and not data.get("done"):
    q = data.get("question", {})
    qid = q.get("id")
    qtype = q.get("type")
    options = q.get("options", []) or []

    if not qid:
        print("  No more questions")
        break

    if options:
        answer = options[0]
    elif qtype in ("rating_1_5", "scale", "ege"):
        answer = "3"
    elif qtype == "salary":
        answer = "100000"
    else:
        answer = "Да"

    status, data = post("/api/v1/answer", {
        "session_id": session_id,
        "question_id": qid,
        "answer": answer,
    })
    answered += 1
    done = data.get("done")
    next_q = data.get("question", {})
    progress = next_q.get("progress", {})
    print(f"  [{answered}] type={qtype} status={status} done={done} progress={progress}")
    if done:
        print(f"  Survey completed!")
        recs = data.get("recommendations", [])
        print(f"  Recommendations: {len(recs) if recs else 0}")
        if recs:
            top = recs[0]
            print(f"  Top: {top.get('name', '')} ({top.get('probability', 0)})")
        break
    if not next_q:
        print("  No next question")
        break

print(f"\nTotal answers submitted: {answered}")

print("\n=== Admin API ===")
status, data = post("/api/admin/auth/login", {"username": "admin", "password": "admin123"})
token = data.get("token", "")[:50]
print(f"POST /api/admin/auth/login -> {status}, token: {token}...")

status, data = get("/api/admin/settings")
s = data.get("settings", {})
print(f"GET /api/admin/settings -> {status}")
print(f"  university_name: {s.get('university_name')}")
print(f"  contact_email: '{s.get('contact_email')}'")
print(f"  support_phone: '{s.get('support_phone')}'")

print("\n=== All tests passed ===")
