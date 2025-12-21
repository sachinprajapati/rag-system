from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_document_upload():
    response = client.post("/documents/upload", files={"file": ("test.pdf", open("test.pdf", "rb"))})
    assert response.status_code == 200
    assert "document_id" in response.json()

def test_query_endpoint():
    response = client.post("/query", json={"query": "What is the capital of France?"})
    assert response.status_code == 200
    assert "results" in response.json()