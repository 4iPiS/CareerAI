import requests

# Login
login = requests.post("http://localhost:7777/api/admin/login", json={
    "username": "admin",
    "password": "admin123"
})
token = login.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Get current settings
resp = requests.get("http://localhost:7777/api/admin/recommender-settings", headers=headers)
settings = resp.json()["settings"]
print("Current system_prompt:", repr(settings.get("system_prompt", "")[:100]))

# Update with default prompt
prompt = """Ты — опытный карьерный консультант для абитуриентов. Твоя задача — помочь абитуриенту выбрать подходящие направления обучения.

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
  - Верни ТОЛЬКО JSON массив, без дополнительного текста."""

requests.put("http://localhost:7777/api/admin/recommender-settings", headers=headers, json={
    "system_prompt": prompt
})

# Verify
resp2 = requests.get("http://localhost:7777/api/admin/recommender-settings", headers=headers)
settings2 = resp2.json()["settings"]
print("Updated system_prompt:", repr(settings2.get("system_prompt", "")[:100]))
