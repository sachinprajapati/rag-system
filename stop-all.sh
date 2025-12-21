#!/bin/bash

# Stop All Services Script for RAG System

echo "Stopping RAG System services..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Stop backend
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo -n "Stopping Backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        echo -e " ${GREEN}✓${NC}"
    fi
    rm logs/backend.pid
fi

# Stop frontend
if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo -n "Stopping Frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        echo -e " ${GREEN}✓${NC}"
    fi
    rm logs/frontend.pid
fi

# Stop Docker services
echo -n "Stopping Docker services (Keycloak, Redis)..."
docker-compose down
echo -e " ${GREEN}✓${NC}"

echo ""
echo -e "${GREEN}All services stopped successfully!${NC}"
