$items = Get-ChildItem "C:\Users\Администратор\Desktop\Новая папка (2)\CareerAI\frontend" -Recurse -File -ErrorAction SilentlyContinue
$sum = ($items | Measure-Object -Property Length -Sum).Sum
Write-Host "Frontend size: $([math]::Round($sum/1MB, 1)) MB"
