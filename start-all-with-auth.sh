#!/bin/bash

# Quick Start Script for RAG System with Keycloak Authentication
# This script starts all services in the correct order

set -e

echo "=========================================="
echo "RAG System - Quick Start"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found. Please run from project root.${NC}"
    exit 1
fi

# Function to check if service is running
check_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $name to start..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|404\|401"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}✗${NC}"
    echo -e "${RED}Failed to start $name after $max_attempts attempts${NC}"
    return 1
}

echo ""
echo "Step 1: Starting Keycloak..."
echo "------------------------------"
docker-compose up -d keycloak
check_service "http://localhost:8080" "Keycloak"

echo ""
echo "Step 2: Starting Redis..."
echo "-------------------------"
docker-compose up -d redis
sleep 2
echo -e "${GREEN}Redis started ✓${NC}"

echo ""
echo "Step 3: Starting Backend..."
echo "---------------------------"
cd backend

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    uv venv
fi

# Check if dependencies are installed
if [ ! -f ".venv/installed" ]; then
    echo "Installing Python dependencies..."
    uv pip install -r requirements.txt
    touch .venv/installed
fi

echo "Starting FastAPI backend..."
nohup uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../logs/backend.pid

cd ..
check_service "http://localhost:8000/api/health" "Backend"

echo ""
echo "Step 4: Starting Frontend..."
echo "----------------------------"
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

echo "Starting Vite dev server..."
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../logs/frontend.pid

cd ..
check_service "http://localhost:3000" "Frontend"

echo ""
echo "=========================================="
echo -e "${GREEN}All services started successfully!${NC}"
echo "=========================================="
echo ""
echo "Service URLs:"
echo "  • Frontend:        http://localhost:3000"
echo "  • Backend API:     http://localhost:8000"
echo "  • API Docs:        http://localhost:8000/docs"
echo "  • Keycloak Admin:  http://localhost:8080"
echo ""
echo "Default Credentials:"
echo "  Keycloak Admin:  admin / admin"
echo "  Test User:       user@rag.local / user123"
echo "  Test Admin:      admin@rag.local / admin123"
echo ""
echo "Next Steps:"
echo "  1. Configure Keycloak (if first time): See KEYCLOAK_SETUP.md"
echo "  2. Open http://localhost:3000 in your browser"
echo "  3. Click 'Login' and authenticate"
echo ""
echo "Process IDs:"
echo "  Backend PID:  $BACKEND_PID (see logs/backend.log)"
echo "  Frontend PID: $FRONTEND_PID (see logs/frontend.log)"
echo ""
echo "To stop all services, run:"
echo "  ./stop-all.sh"
echo ""
echo -e "${YELLOW}Note: First-time setup requires Keycloak configuration.${NC}"
echo -e "${YELLOW}Follow instructions in KEYCLOAK_SETUP.md${NC}"
echo "=========================================="
