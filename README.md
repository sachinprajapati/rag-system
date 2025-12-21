# Production-Grade RAG System

A full-stack Retrieval-Augmented Generation (RAG) system built with FastAPI, React, Celery, and Redis.

## 🏗️ Architecture

### Backend
- **FastAPI**: High-performance async API framework
- **Celery + Redis**: Distributed task queue for document processing
- **PyMUPDF**: PDF parsing and text extraction
- **LangChain**: Text splitting and chunking
- **Sentence Transformers**: all-MiniLM-L6-v2 embeddings model
- **FAISS**: Vector database for similarity search

### Frontend
- **React**: Modern UI framework
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- Redis server

## 🚀 Quick Start (Local Development)

### 1. Install Dependencies

```bash
# Run the quick setup script
./quick-setup.sh
```

This will:
- Create a Python virtual environment
- Install all Python dependencies (CPU-optimized PyTorch)
- Create necessary directories

### 2. Configure Environment

The `.env` file is already created with local development settings:
```env
REDIS_URL=redis://localhost:6379/0
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=512
```

### 3. Start Services

#### Option A: All-in-One Script
```bash
./start-all.sh
```

#### Option B: Manual Start (Recommended for Development)

**Terminal 1 - Redis** (if not running):
```bash
redis-server
```

**Terminal 2 - Celery Worker**:
```bash
cd backend
source venv/bin/activate
celery -A src.tasks.celery_app worker --loglevel=info
```

**Terminal 3 - FastAPI Backend**:
```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 4 - React Frontend** (optional):
```bash
cd frontend
npm install  # first time only
npm run dev
```

## 📡 API Endpoints

Access the API at: `http://localhost:8000`

### Interactive Docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

#### Health Check
```bash
GET /api/health
```

#### Upload Document
```bash
POST /api/documents/upload
Content-Type: multipart/form-data

{
  "file": <PDF file>
}
```

#### Query Documents
```bash
POST /api/query
Content-Type: application/json

{
  "query": "Your question here",
  "top_k": 5
}
```

#### List Documents
```bash
GET /api/documents
```

## 🧪 Testing

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

```
rag-system
├── backend
│   ├── src
│   │   ├── main.py                # Entry point for the FastAPI application
│   │   ├── api                    # API routes and dependencies
│   │   │   ├── routes             # API route definitions
│   │   │   ├── dependencies.py     # Dependency functions for API routes
│   │   ├── core                   # Core application logic
│   │   ├── services               # Business logic for document ingestion, embeddings, retrieval, and generation
│   │   ├── tasks                  # Celery tasks for asynchronous processing
│   │   ├── models                 # Data models for documents and queries
│   │   ├── db                     # Database interactions (FAISS and Redis)
│   │   └── utils                  # Utility functions for text splitting and PDF parsing
│   ├── tests                      # Unit tests for the application
│   ├── requirements.txt           # Python dependencies for the backend
│   ├── pyproject.toml             # Project metadata and dependency management
│   └── Dockerfile                 # Docker image for the backend application
├── frontend
│   ├── src                        # React application source code
│   ├── public                     # Public assets for the React application
│   ├── package.json               # npm dependencies and scripts for the frontend
│   ├── tsconfig.json              # TypeScript configuration for the frontend
│   ├── vite.config.ts             # Vite configuration for the frontend
│   └── Dockerfile                 # Docker image for the frontend application
├── docker-compose.yml             # Docker Compose configuration for the application
├── .env.example                   # Example environment variables
├── .gitignore                     # Git ignore file
└── README.md                     # Project documentation
```

## Technologies Used

- **Backend**: FastAPI, Celery, Redis, PyMuPDF, LangChain, FAISS
- **Frontend**: React, TypeScript
- **Database**: FAISS for vector storage, Redis for task management
- **Document Processing**: PyMuPDF for PDF ingestion and LangChain for text splitting

## Getting Started

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd rag-system
   ```

2. **Set up the backend**:
   - Navigate to the `backend` directory.
   - Install dependencies:
     ```
     pip install -r requirements.txt
     ```
   - Run the FastAPI application:
     ```
     uvicorn src.main:app --reload
     ```

3. **Set up the frontend**:
   - Navigate to the `frontend` directory.
   - Install dependencies:
     ```
     npm install
     ```
   - Start the React application:
     ```
     npm run dev
     ```

4. **Run with Docker**:
   - Use Docker Compose to run the entire application:
     ```
     docker-compose up --build
     ```

## API Endpoints

- **Document Ingestion**: Upload documents for processing.
- **Query Interface**: Submit queries to retrieve relevant information from ingested documents.
- **Health Check**: Check the status of the application.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.