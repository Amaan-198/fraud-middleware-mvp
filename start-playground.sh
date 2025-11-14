#!/bin/bash

# Security & Fraud Playground - Quick Start Script
# This script starts both the backend API and frontend UI

set -e

echo "🚀 Starting Allianz Fraud Middleware Playground..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Python
echo -e "${BLUE}[1/5]${NC} Checking Python..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo -e "${RED}❌ Python is required but not installed.${NC}"
        echo "Press any key to exit..."
        read -n 1
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi
echo -e "${GREEN}✓ Python found: $PYTHON_CMD${NC}"

# Check Node.js
echo -e "${BLUE}[2/5]${NC} Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is required but not installed.${NC}"
    echo "Download from: https://nodejs.org/"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi
echo -e "${GREEN}✓ Node.js found: $(node --version)${NC}"

# Create logs directory
mkdir -p logs

# Install Python dependencies
echo -e "${BLUE}[3/5]${NC} Installing Python dependencies..."
$PYTHON_CMD -m pip install --quiet --disable-pip-version-check fastapi uvicorn pydantic numpy scikit-learn onnxruntime aiohttp 2>&1 | tee logs/pip-install.log
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${YELLOW}⚠ Some pip warnings (check logs/pip-install.log)${NC}"
else
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
fi

# Install Frontend dependencies
echo -e "${BLUE}[4/5]${NC} Checking frontend dependencies..."
cd demo/frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (this may take a minute)..."
    npm install 2>&1 | tee ../../logs/npm-install.log
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo -e "${RED}❌ Failed to install frontend dependencies${NC}"
        cd ../..
        echo "Press any key to exit..."
        read -n 1
        exit 1
    fi
fi
cd ../..
echo -e "${GREEN}✓ Frontend dependencies ready${NC}"

# Start services
echo -e "${BLUE}[5/5]${NC} Starting services..."
echo ""

# Function to kill processes on port (cross-platform)
kill_port() {
    local port=$1
    # Try different methods to kill process on port
    if command -v lsof &> /dev/null; then
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    else
        # Windows/Git Bash fallback
        netstat -ano | grep ":$port " | awk '{print $5}' | xargs -r taskkill //PID //F 2>/dev/null || true
    fi
}

# Kill any existing processes
echo "Checking for existing processes..."
kill_port 8000
kill_port 5173
sleep 1

# Start backend
echo -e "${GREEN}📡 Starting Backend API on http://localhost:8000${NC}"
$PYTHON_CMD -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
echo $BACKEND_PID > logs/backend.pid

# Wait for backend to be ready with better error handling
echo -n "   Waiting for backend to start"
BACKEND_READY=0
for i in {1..30}; do
    sleep 1
    echo -n "."

    # Check if process is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e " ${RED}✗${NC}"
        echo -e "${RED}❌ Backend process died. Check logs/backend.log for errors${NC}"
        echo ""
        echo "Last 20 lines of backend.log:"
        tail -20 logs/backend.log
        echo ""
        echo "Press any key to exit..."
        read -n 1
        exit 1
    fi

    # Check if backend is responding
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        BACKEND_READY=1
        echo -e " ${GREEN}✓${NC}"
        break
    fi
done

if [ $BACKEND_READY -eq 0 ]; then
    echo -e " ${RED}✗${NC}"
    echo -e "${YELLOW}⚠ Backend taking longer than expected. Check logs/backend.log${NC}"
    echo ""
    echo "Last 20 lines of backend.log:"
    tail -20 logs/backend.log
    echo ""
    echo "Continue anyway? (y/n)"
    read -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
fi

# Start frontend
echo -e "${GREEN}🎨 Starting Frontend UI on http://localhost:5173${NC}"
cd demo/frontend
npm run dev > ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..
echo "   Frontend PID: $FRONTEND_PID"
echo $FRONTEND_PID > logs/frontend.pid

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Playground is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BLUE}Frontend:${NC}  http://localhost:5173"
echo -e "  ${BLUE}Backend:${NC}   http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC}  http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Features:${NC}"
echo "  • Fraud Detection Testing"
echo "  • Security Events Monitor"
echo "  • SOC Analyst Workspace"
echo "  • Rate Limiting Playground"
echo ""
echo -e "${YELLOW}To stop:${NC} Run ./stop-playground.sh or press Ctrl+C"
echo ""
echo -e "📋 Logs: logs/backend.log and logs/frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo -e '${YELLOW}Stopping playground...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'; exit 0" INT TERM

# Keep script running
wait
