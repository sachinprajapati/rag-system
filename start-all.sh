#!/bin/bash

# Start all services for RAG System

echo "🚀 Starting RAG System Services..."

# Check if Redis is running
if ! pgrep -x redis-server > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

echo "✓ Redis is running"

# Start Celery worker in background
echo "Starting Celery worker..."
cd backend
source .venv/bin/activate 2>/dev/null || true

celery -A src.tasks.celery_app worker --loglevel=info > logs/celery.log 2>&1 &
CELERY_PID=$!
echo "✓ Celery worker started (PID: $CELERY_PID)"

# Start FastAPI backend
echo "Starting FastAPI backend..."
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "✓ Backend started (PID: $BACKEND_PID)"

cd ..

# Start Frontend if npm is available
if command -v npm &> /dev/null && [ -d "frontend/node_modules" ]; then
    echo "Starting React frontend..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    echo "✓ Frontend started (PID: $FRONTEND_PID)"
    cd ..
fi

echo ""
echo "=============================================="
echo "✅ RAG System is running!"
echo "=============================================="
echo ""
echo "Services:"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Frontend: http://localhost:3000 (if installed)"
echo ""
echo "To stop all services:"
echo "  kill $CELERY_PID $BACKEND_PID"
echo ""
echo "Press Ctrl+C to stop the backend..."

# Wait for backend process
wait $BACKEND_PID
