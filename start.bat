@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
echo Starting InsideLens on http://127.0.0.1:8000 ...
python -m uvicorn app.main:app --reload --port 8000
