@echo off
REM Security & Fraud Playground - Windows Startup Script
REM Simple Windows batch file for starting the playground

echo ========================================
echo  Allianz Fraud Middleware Playground
echo ========================================
echo.

REM Create logs directory
if not exist logs mkdir logs

REM Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)
echo OK - Python found
echo.

REM Check Node.js
echo [2/4] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)
echo OK - Node.js found
echo.

REM Install Python dependencies
echo [3/4] Installing Python dependencies...
python -m pip install --quiet fastapi uvicorn pydantic numpy scikit-learn onnxruntime aiohttp
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
)
echo OK - Python dependencies ready
echo.

REM Install Frontend dependencies
echo [4/4] Checking frontend dependencies...
cd demo\frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies
        cd ..\..
        pause
        exit /b 1
    )
)
cd ..\..
echo OK - Frontend dependencies ready
echo.

echo ========================================
echo  Starting Services
echo ========================================
echo.

REM Kill any existing processes on ports
echo Checking for existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 >nul

REM Start backend
echo Starting Backend API...
start "Fraud Middleware Backend" /min cmd /c "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > logs\backend.log 2>&1"
echo Backend starting on http://localhost:8000
echo.

REM Wait for backend
echo Waiting for backend to be ready...
timeout /t 5 >nul

REM Test backend health
:CHECK_BACKEND
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo Backend not ready yet, waiting...
    timeout /t 2 >nul
    goto CHECK_BACKEND
)
echo Backend is ready!
echo.

REM Start frontend
echo Starting Frontend UI...
cd demo\frontend
start "Fraud Middleware Frontend" /min cmd /c "npm run dev > ..\..\logs\frontend.log 2>&1"
cd ..\..
echo Frontend starting on http://localhost:5173
echo.

echo ========================================
echo  Playground is Running!
echo ========================================
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo Features:
echo   * Fraud Detection Testing
echo   * Security Events Monitor
echo   * SOC Analyst Workspace
echo   * Rate Limiting Playground
echo.
echo To stop: Run stop-playground.bat
echo.
echo Opening browser in 3 seconds...
timeout /t 3 >nul
start http://localhost:5173
echo.
echo Press any key to exit (services will keep running)...
pause >nul
