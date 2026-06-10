@echo off
call "%~dp0..\venv\Scripts\activate.bat"
set PYTHONPATH=%~dp0..
python "%~dp0..\run.py"
