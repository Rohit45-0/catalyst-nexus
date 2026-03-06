@echo off
setlocal

echo ============================================
echo   Catalyst Nexus - Stop Dev Servers
echo ============================================

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  echo Stopping backend PID %%p (port 8000)
  taskkill /F /PID %%p >nul 2>&1
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
  echo Stopping frontend PID %%p (port 5173)
  taskkill /F /PID %%p >nul 2>&1
)

echo Done.

endlocal
