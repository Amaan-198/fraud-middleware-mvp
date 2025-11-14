#!/bin/bash

# Security & Fraud Playground - Startup Script
# Starts the React development server

echo "=================================="
echo "Security & Fraud Playground UI"
echo "=================================="
echo ""
echo "Starting development server..."
echo "The playground will be available at: http://localhost:3000"
echo ""
echo "Make sure the backend API is running on http://localhost:8000"
echo "You can start the backend with: uvicorn api.main:app --reload"
echo ""

cd "$(dirname "$0")"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the dev server
npm run dev
