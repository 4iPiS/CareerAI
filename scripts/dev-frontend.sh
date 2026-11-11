#!/bin/bash
# Скрипт для локальной разработки React
# Запуск: ./scripts/dev-frontend.sh

set -e

echo "🚀 Запуск React dev server..."
cd frontend
npm install
npm run dev
