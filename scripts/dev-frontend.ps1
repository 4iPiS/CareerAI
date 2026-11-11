# Скрипт для локальной разработки React (PowerShell)
# Запуск: .\scripts\dev-frontend.ps1

Write-Host "🚀 Запуск React dev server..." -ForegroundColor Green
Set-Location frontend
npm install
npm run dev
