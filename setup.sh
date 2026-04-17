#!/bin/bash

# Payment Tracking Dashboard - Quick Start Script

echo "🚀 Payment Tracking Dashboard - Quick Start"
echo "==========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 16+"
    exit 1
fi

# Check MongoDB
if ! command -v mongod &> /dev/null; then
    echo "⚠️  MongoDB not found locally. Make sure MongoDB is running!"
    echo "   You can use MongoDB Atlas or local MongoDB."
fi

echo "✓ Prerequisites check passed"

# Setup Backend
echo ""
echo "📦 Setting up Backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Created virtual environment"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -q
echo "✓ Installed backend dependencies"

# Create .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file from template"
fi

# Setup Frontend
echo ""
echo "📦 Setting up Frontend..."
cd ../frontend

# Install dependencies
npm install -q
echo "✓ Installed frontend dependencies"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "1. Start MongoDB (if not already running)"
echo "2. In terminal 1: cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload"
echo "3. In terminal 2: cd frontend && npm run dev"
echo ""
echo "Then open: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
