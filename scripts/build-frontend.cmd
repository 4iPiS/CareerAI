@echo off
rem ============================================================
rem  Сборка фронтенда БЕЗ node_modules на диске:
rem  зависимости ставятся внутри временного node-контейнера,
rem  на хост попадает только готовый frontend/dist.
rem  Использование: scripts\build-frontend.cmd
rem ============================================================
setlocal
cd /d "%~dp0.."

echo [1/5] Подготовка временного node-контейнера...
docker rm -f fe-builder >nul 2>&1
docker create --name fe-builder node:20-alpine sleep infinity >nul
docker start fe-builder >nul

echo [2/5] Копирование исходников фронтенда в контейнер...
docker cp frontend\. fe-builder:/app

echo [3/5] npm install + сборка (2-4 минуты)...
docker exec fe-builder sh -c "cd /app && npm install --silent && npm run build"
if errorlevel 1 (
    echo ОШИБКА СБОРКИ
    docker rm -f fe-builder >nul 2>&1
    exit /b 1
)

echo [4/5] Забираем dist на хост...
if exist frontend\dist rmdir /s /q frontend\dist
docker cp fe-builder:/app/dist frontend\dist

echo [5/5] Очистка...
docker rm -f fe-builder >nul 2>&1

echo ГОТОВО: frontend\dist обновлён. node_modules на диске не создаётся.
endlocal
