#!/bin/bash

# Stop the Security & Fraud Playground

echo "🛑 Stopping Allianz Fraud Middleware Playground..."

# Kill processes by PID if files exist
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    kill $BACKEND_PID 2>/dev/null && echo "✓ Backend stopped (PID: $BACKEND_PID)"
    rm logs/backend.pid
fi

if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    kill $FRONTEND_PID 2>/dev/null && echo "✓ Frontend stopped (PID: $FRONTEND_PID)"
    rm logs/frontend.pid
fi

# Also kill by port in case PID files don't exist
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✓ Killed process on port 8000"
lsof -ti:5173 | xargs kill -9 2>/dev/null && echo "✓ Killed process on port 5173"

echo "✓ Playground stopped"
