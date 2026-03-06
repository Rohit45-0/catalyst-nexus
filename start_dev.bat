@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo ============================================
echo   Catalyst Nexus - Start Dev Servers
echo ============================================
echo Root: %ROOT%
echo.

echo [1/2] Starting backend on http://localhost:8000
start "Catalyst Backend" cmd /k "set PYTHONPATH=%ROOT% && cd /d %ROOT% && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"

echo [2/2] Starting frontend on http://localhost:5173
start "Catalyst Frontend" cmd /k "cd /d %ROOT%\frontend && npm run dev -- --host 0.0.0.0 --port 5173"

echo.
echo Launched in separate terminal windows.
echo Frontend: http://localhost:5173
echo Backend Docs: http://localhost:8000/docs
echo.
echo NOTE: Keep those terminal windows open while testing.

endlocal
