@echo off
REM Stop the Security & Fraud Playground - Windows Version

echo Stopping Allianz Fraud Middleware Playground...
echo.

REM Kill processes by port
echo Stopping backend (port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 echo   Stopped process %%a
)

echo Stopping frontend (port 5173)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173') do (
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 echo   Stopped process %%a
)

REM Kill by window title
taskkill /FI "WINDOWTITLE eq Fraud Middleware Backend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Fraud Middleware Frontend" /F >nul 2>&1

echo.
echo Playground stopped.
pause
