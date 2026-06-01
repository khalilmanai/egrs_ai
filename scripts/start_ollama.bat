@echo off
echo Checking if Ollama is installed...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama not found. Download from https://ollama.com
    start https://ollama.com
    exit /b 1
)

echo Pulling Qwen model (this may take a few minutes)...
ollama pull qwen2.5:3b

echo.
echo Ollama is ready! Model qwen2.5:3b is available.
echo Start the AI service with: python run.py
pause
