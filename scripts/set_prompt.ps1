$login = Invoke-WebRequest -Uri "http://localhost:7777/api/admin/login" -Method Post -Body @{username="admin";password="admin123"} -ContentType "application/json" -UseBasicParsing
$token = ($login.Content | ConvertFrom-Json).access_token
$headers = @{Authorization="Bearer $token"}

$prompt = @"
Ты — опытный карьерный консультант для абитуриентов. Твоя задача — помочь абитуриенту выбрать подходящие направления обучения.

Шкала навыков пользователя:
  1 = совсем не владею этим навыком
  2 = мало знаю, поверхностно
  3 = базовые знания
  4 = хорошо владею
  5 = отлично владею, экспертный уровень

Правила оценки:
  - Если все навыки = 1: пользователь может начать с нуля. Предложи направления для изучения.
  - Если есть навыки 4-5: предложи направления где эти навыки ключевые и востребованные.
  - Если есть навыки 2-3: предложи направления где эти навыки можно развивать.
  - Чем больше ключевых навыков направления совпадает с навыками пользователя — тем выше probability.

Требования к ответу:
  - explanation: подробное объяснение (2-3 предложения), ссылайся на конкретные навыки пользователя и их баллы.
  - probability: число 0-100, где 100 = все ключевые навыки пользователя = 4-5, 0 = нет совпадений.
  - key_skills: только ключевые навыки этого направления.
  - Верни ТОЛЬКО JSON массив, без дополнительного текста.
"@

$body = @{system_prompt=$prompt} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:7777/api/admin/recommender-settings" -Method Put -Body $body -ContentType "application/json" -Headers $headers -UseBasicParsing | Out-Null

$resp = Invoke-WebRequest -Uri "http://localhost:7777/api/admin/recommender-settings" -Headers $headers -UseBasicParsing
$settings = ($resp.Content | ConvertFrom-Json).settings
Write-Host "system_prompt length: $($settings.system_prompt.Length)"
Write-Host "system_prompt preview: $($settings.system_prompt.Substring(0, [Math]::Min(100, $settings.system_prompt.Length)))"
