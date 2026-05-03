@echo off
REM Run backend (Windows cmd)
REM Adjust the venv path if your virtualenv is in the repository root (.venv) or inside backend (.venv)
SETLOCAL
if exist "%~dp0..\.venv\Scripts\activate.bat" (
  call "%~dp0..\.venv\Scripts\activate.bat"
) else if exist "%~dp0.venv\Scripts\activate.bat" (
  call "%~dp0.venv\Scripts\activate.bat"
) else (
  echo Warning: virtualenv activation script not found. Make sure to activate your venv manually.
)

echo Installing dependencies (skip this step if already installed)...
pip install -r "%~dp0requirements.txt"

echo Starting backend (uvicorn)...
cd /d "%~dp0"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
ENDLOCAL
