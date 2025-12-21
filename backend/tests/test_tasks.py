from fastapi.testclient import TestClient
from backend.src.main import app
from backend.src.tasks.document_processing import process_document

client = TestClient(app)

def test_process_document():
    response = client.post("/api/documents/process", json={"document_id": "test_doc_id"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Document processed successfully."}

def test_failed_process_document():
    response = client.post("/api/documents/process", json={"document_id": "invalid_doc_id"})
    assert response.status_code == 400
    assert response.json() == {"status": "error", "message": "Document not found."}