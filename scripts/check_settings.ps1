$body = @{username="admin";password="admin123"} | ConvertTo-Json
$login = Invoke-WebRequest -Uri "http://localhost:7777/api/admin/auth/login" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
$token = ($login.Content | ConvertFrom-Json).token
$headers = @{Authorization="Bearer $token"}

# Get current settings
$resp = Invoke-WebRequest -Uri "http://localhost:7777/api/admin/recommender-settings" -Headers $headers -UseBasicParsing
$settings = ($resp.Content | ConvertFrom-Json).settings
Write-Host "system_prompt length: $($settings.system_prompt.Length)"
if ($settings.system_prompt.Length -gt 0) {
    Write-Host "system_prompt preview: $($settings.system_prompt.Substring(0, [Math]::Min(80, $settings.system_prompt.Length)))"
} else {
    Write-Host "system_prompt is EMPTY"
}
