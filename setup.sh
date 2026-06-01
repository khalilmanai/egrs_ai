#!/bin/bash
echo "=== EGRS AI Service Setup ==="

python3 --version || { echo "Python 3.11+ required"; exit 1; }

[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Make sure Ollama is running: ollama pull qwen2.5:3b"
echo "  2. Start the AI service: python run.py"
echo "  3. Open http://localhost:8000/docs"
