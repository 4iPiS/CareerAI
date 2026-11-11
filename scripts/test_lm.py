$body = @{
    model = 'qwen2.5-vl-3b-instruct'
    messages = @(
        @{role='system'; content='Return ONLY a JSON array. Each item has: field (string), probability (number 0-100), explanation (string), key_skills (array of strings). No other text.'},
        @{role='user'; content='Test response'}
    )
    temperature = 0.3
    max_tokens = 500
} | ConvertTo-Json -Depth 10

Write-Host $body
$result = Invoke-WebRequest -Uri "http://localhost:1234/v1/chat/completions" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
Write-Host $result.Content
