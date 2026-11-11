import httpx, json, re

resp = httpx.post(
    "http://host.docker.internal:1234/v1/chat/completions",
    json={
        "model": "qwen2.5-vl-3b-instruct",
        "messages": [
            {"role": "system", "content": "Return ONLY a JSON array. Each item: field (string), probability (number 0-100), explanation (string), key_skills (array of strings). No other text."},
            {"role": "user", "content": "Test response only"}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    },
    timeout=30
)
data = resp.json()
content = data["choices"][0]["message"]["content"]
print("=== RAW CONTENT ===")
print(repr(content[:1000]))
print()
print("=== TRYING PARSE ===")

# Simulate our parser
text = content.strip()
if text.startswith("```"):
    lines = text.split("\n")
    lines = lines[1:] if lines[0].startswith("```") else lines
    lines = lines[:-1] if lines[-1].strip() == "```" else lines
    text = "\n".join(lines).strip()
print("After markdown strip:")
print(repr(text[:500]))
try:
    result = json.loads(text)
    print("JSON OK:", json.dumps(result, indent=2)[:500])
except json.JSONDecodeError as e:
    print("JSON FAIL:", e)
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        print("Regex found:", repr(match.group()[:300]))
        try:
            result = json.loads(match.group())
            print("Regex JSON OK:", json.dumps(result, indent=2)[:300])
        except json.JSONDecodeError as e2:
            print("Regex JSON FAIL:", e2)
    else:
        print("No regex match")
