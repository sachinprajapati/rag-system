from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import documents, query, health, auth
from src.core.config import settings
from src.core.tenant_isolation import TenantIsolationMiddleware

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
)

# CORS middleware - allow Keycloak and frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",  # Keycloak
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant isolation middleware for multi-tenant security
app.add_middleware(TenantIsolationMiddleware)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(query.router, prefix="/api/query", tags=["query"])

@app.get("/")
async def root():
    return {
        "message": "RAG System API",
        "version": settings.API_VERSION,
        "docs": "/docs",
    }