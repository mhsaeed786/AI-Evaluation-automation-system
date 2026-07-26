@echo off
echo Starting OneAgent Local...
echo.
echo Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Ollama is not running. Start it first: ollama serve
    echo.
)
echo Starting Streamlit on port 8502...
cd /d "%~dp0"
python -m streamlit run app.py --server.port 8502
pause
