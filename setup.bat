@echo off
REM Payment Tracking Dashboard - Quick Start Script for Windows

echo 🚀 Payment Tracking Dashboard - Quick Start
echo ===========================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.9+
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Please install Node.js 16+
    exit /b 1
)

echo ✓ Prerequisites check passed

REM Setup Backend
echo.
echo 📦 Setting up Backend...
cd backend

REM Create virtual environment
if not exist "venv" (
    python -m venv venv
    echo ✓ Created virtual environment
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
pip install -r requirements.txt -q
echo ✓ Installed backend dependencies

REM Create .env if not exists
if not exist ".env" (
    copy .env.example .env
    echo ✓ Created .env file from template
)

REM Setup Frontend
echo.
echo 📦 Setting up Frontend...
cd ..\frontend

REM Install dependencies
call npm install -q
echo ✓ Installed frontend dependencies

echo.
echo ✅ Setup complete!
echo.
echo To start the application:
echo 1. Start MongoDB (if not already running)
echo 2. In PowerShell/CMD 1: cd backend, venv\Scripts\activate, python -m uvicorn app.main:app --reload
echo 3. In PowerShell/CMD 2: cd frontend, npm run dev
echo.
echo Then open: http://localhost:3000
echo API Docs: http://localhost:8000/docs
