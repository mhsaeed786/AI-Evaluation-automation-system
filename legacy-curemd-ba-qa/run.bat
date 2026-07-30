@echo off
title HealthOS BA QA Automation Suite
color 0A
echo ============================================
echo   HealthOS BA/QA Automation Suite Launcher
echo ============================================
echo.
cd /d %~dp0

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [2/3] Installing dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo WARNING: Some dependencies failed to install.
    echo Attempting to continue...
)

echo [3/3] Launching Streamlit application...
echo.
echo Opening browser at http://localhost:8501
echo Press Ctrl+C to stop the server.
echo.
streamlit run ui/app.py --server.port 8501 --browser.gatherUsageStats false
pause
