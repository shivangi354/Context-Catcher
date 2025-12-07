#!/bin/bash

# ContextCatcher Quick Start Script

echo "======================================"
echo "  ContextCatcher MVP - Quick Start"
echo "======================================"
echo

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "⚠️  config.json not found!"
    echo "Creating from example..."
    cp config.example.json config.json
    echo "✓ Created config.json"
    echo
    echo "⚠️  IMPORTANT: Edit config.json with your email credentials before continuing!"
    echo "   For Gmail: Use an app-specific password (see README.md)"
    echo
    read -p "Press Enter after you've configured config.json..."
fi

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi
echo "✓ Python found"
echo

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies already installed"
fi
echo

# Create storage directory
mkdir -p storage
echo "✓ Storage directory ready"
echo

# Start backend in background
echo "Starting FastAPI backend..."
python3 backend/main.py &
BACKEND_PID=$!
echo "✓ Backend started (PID: $BACKEND_PID)"
echo

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
for i in {1..10}; do
    curl -s http://localhost:8000/status > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ Backend is ready"
        break
    fi
    sleep 1
done

# Start Streamlit UI
echo
echo "Starting Streamlit UI..."
echo "======================================"
echo
streamlit run ui/app.py

# Cleanup on exit
echo
echo "Shutting down..."
kill $BACKEND_PID 2>/dev/null
echo "✓ Backend stopped"
echo "Goodbye!"
