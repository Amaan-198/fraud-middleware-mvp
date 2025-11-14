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
    echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python found${NC}"

# Check Node.js
echo -e "${BLUE}[2/5]${NC} Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js found${NC}"

# Install Python dependencies
echo -e "${BLUE}[3/5]${NC} Installing Python dependencies..."
pip install -q fastapi uvicorn pydantic numpy scikit-learn onnxruntime aiohttp 2>/dev/null || true
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Install Frontend dependencies
echo -e "${BLUE}[4/5]${NC} Installing frontend dependencies..."
cd demo/frontend
if [ ! -d "node_modules" ]; then
    npm install --silent 2>/dev/null || npm install
fi
cd ../..
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# Start services
echo -e "${BLUE}[5/5]${NC} Starting services..."
echo ""

# Kill any existing processes on ports 8000 and 5173
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Start backend
echo -e "${GREEN}📡 Starting Backend API on http://localhost:8000${NC}"
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to be ready
echo -n "   Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    sleep 1
    echo -n "."
done

# Start frontend
echo -e "${GREEN}🎨 Starting Frontend UI on http://localhost:5173${NC}"
cd demo/frontend
npm run dev > ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..
echo "   Frontend PID: $FRONTEND_PID"

# Save PIDs
mkdir -p logs
echo $BACKEND_PID > logs/backend.pid
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

# Wait for Ctrl+C
trap "echo ''; echo -e '${YELLOW}Stopping playground...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# Keep script running
wait
