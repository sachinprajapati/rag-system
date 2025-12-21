"""PDF parsing utilities using PyMuPDF (fitz)"""
import fitz  # PyMuPDF
from typing import Union
from pathlib import Path


def parse_pdf(file_path: Union[str, Path]) -> str:
    """
    Extract text from PDF file using PyMuPDF.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text content
    """
    text_content = []
    
    try:
        # Open the PDF
        doc = fitz.open(file_path)
        
        # Extract text from each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_content.append(page.get_text())
        
        doc.close()
        
    except Exception as e:
        raise ValueError(f"Error parsing PDF: {str(e)}")
    
    return "\n\n".join(text_content).strip()