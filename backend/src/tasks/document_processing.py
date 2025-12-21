from celery import shared_task
import fitz  # PyMuPDF
from backend.src.services.document_ingestion import ingest_document
from backend.src.utils.pdf_parser import parse_pdf
from backend.src.utils.text_splitter import split_text
from backend.src.db.faiss_manager import add_embeddings_to_faiss

@shared_task
def process_document(file_path):
    document_text = parse_pdf(file_path)
    chunks = split_text(document_text)
    
    for chunk in chunks:
        embedding = ingest_document(chunk)
        add_embeddings_to_faiss(embedding)