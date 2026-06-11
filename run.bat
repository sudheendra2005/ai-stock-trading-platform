@echo off
setlocal EnableExtensions
title NexusAI Trading Platform

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "BACKEND_PY=%BACKEND%\venv\Scripts\python.exe"
set "BACKEND_PIP=%BACKEND%\venv\Scripts\pip.exe"
set "BOOTSTRAP_EPISODES=10"

echo ================================================
echo   NexusAI - AI Stock Trading Platform
echo ================================================
echo.

echo [1/7] Clearing local dev ports...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING" 2^>nul') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5173" ^| find "LISTENING" 2^>nul') do taskkill /F /PID %%a >nul 2>&1

echo [2/7] Preparing backend virtual environment...
cd /d "%BACKEND%"
if not exist "%BACKEND_PY%" (
    python -m venv venv
    if errorlevel 1 goto backend_venv_error
)

echo [3/7] Installing backend dependencies...
"%BACKEND_PY%" -m pip install --upgrade pip --quiet
"%BACKEND_PIP%" install -r requirements.txt --quiet
if errorlevel 1 goto backend_deps_error

echo [4/7] Preparing frontend dependencies...
cd /d "%FRONTEND%"
if exist package-lock.json (
    call npm install
) else (
    call npm install
)
if errorlevel 1 goto frontend_deps_error

echo [5/7] Checking AI market dataset...
set "DATA_READY=0"
if exist "%BACKEND%\data\market_history\AAPL_2y_1d.csv" set "DATA_READY=1"
if "%SKIP_AI_BOOTSTRAP%"=="1" (
    echo AI bootstrap skipped because SKIP_AI_BOOTSTRAP=1.
) else if "%DATA_READY%"=="1" (
    echo Cached market data found. Skipping bootstrap.
) else (
    echo Downloading starter market data and training initial RL policies...
    cd /d "%BACKEND%"
    "%BACKEND_PY%" scripts\bootstrap_market_data.py --episodes %BOOTSTRAP_EPISODES%
    if errorlevel 1 goto bootstrap_error
)

echo [6/7] Starting Backend API (http://localhost:8000)...
start "NexusAI Backend" /D "%BACKEND%" cmd /k ""%BACKEND_PY%" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"

echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo [7/7] Starting Frontend UI (http://localhost:5173)...
start "NexusAI Frontend" /D "%FRONTEND%" cmd /k "call npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo ================================================
echo   App is starting up!
echo   Open: http://localhost:5173
echo ================================================
echo.
echo   Backend API:  http://localhost:8000
echo   API Docs:     http://localhost:8000/docs
echo   Frontend:     http://localhost:5173
echo.
echo   AI data:      backend\data\market_history
echo   RL policies:  database + backend\rl\saved_agents fallback
echo.
echo   Tip: set SKIP_AI_BOOTSTRAP=1 before running this
echo   file if you want to skip first-run data preparation.
echo.
echo   Close both terminal windows to stop the servers.
echo ================================================
echo.
timeout /t 5 /nobreak >nul
start "" "http://localhost:5173"
exit /b 0

:backend_venv_error
echo.
echo ERROR: Could not create backend virtual environment.
pause
exit /b 1

:backend_deps_error
echo.
echo ERROR: Backend dependency installation failed.
pause
exit /b 1

:frontend_deps_error
echo.
echo ERROR: Frontend dependency installation failed.
pause
exit /b 1

:bootstrap_error
echo.
echo ERROR: AI dataset bootstrap failed.
echo You can retry, or run with SKIP_AI_BOOTSTRAP=1 to start the app without bootstrapping.
pause
exit /b 1
