@echo off
title EGRS AI Service Setup
echo === EGRS AI Service Setup (Windows) ===
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo === Setup complete! ===
echo.
echo Next steps:
echo   1. Make sure Ollama is running with: ollama pull qwen2.5:3b
echo   2. Start the AI service with: python run.py
echo   3. Open http://localhost:8000/docs in your browser
echo.
pause
