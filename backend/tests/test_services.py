from fastapi.testclient import TestClient
from backend.src.main import app
from backend.src.services.document_ingestion import ingest_document
from backend.src.services.retrieval import retrieve_documents
from backend.src.services.generation import generate_response

client = TestClient(app)

def test_ingest_document():
    response = client.post("/documents/upload", files={"file": ("test.pdf", open("test.pdf", "rb"))})
    assert response.status_code == 200
    assert response.json() == {"message": "Document ingested successfully"}

def test_retrieve_documents():
    response = client.post("/query", json={"query": "What is the RAG system?"})
    assert response.status_code == 200
    assert "results" in response.json()

def test_generate_response():
    response = client.post("/generate", json={"query": "Explain RAG"})
    assert response.status_code == 200
    assert "response" in response.json()