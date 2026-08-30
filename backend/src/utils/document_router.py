"""Local document classification, extraction, and chunk routing utilities.

The router intentionally uses only local parsers and LangChain text splitters.
It returns plain dictionaries so the vector-store layer stays independent from
LangChain's document abstractions.
"""
from __future__ import annotations

import hashlib
import csv
import io
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from xml.etree import ElementTree

try:  # Keep code/structured uploads usable until PDF extras are installed.
    import pdfplumber
except ImportError:  # pragma: no cover - exercised only in incomplete installs
    pdfplumber = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - exercised only in incomplete installs
    PdfReader = None
from langchain_text_splitters import (
    HTMLHeaderTextSplitter,
    Language,
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


PDF_TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=700,
    chunk_overlap=140,
    separators=["\n\n", "\n", " ", ""],
    length_function=len,
    keep_separator=True,
)

STRUCTURED_EXTENSIONS = {".md", ".markdown", ".html", ".htm", ".xml"}
# LangChain adds languages between releases. Keep member names as strings so an
# older installed release cannot prevent the API from importing (notably SQL is
# absent from some releases).
LANGUAGE_BY_EXTENSION = {
    ".py": "PYTHON",
    ".js": "JS",
    ".jsx": "JS",
    ".ts": "TS",
    ".tsx": "TS",
    ".java": "JAVA",
    ".c": "C",
    ".h": "C",
    ".cpp": "CPP",
    ".cxx": "CPP",
    ".cs": "CSHARP",
    ".go": "GO",
    ".rs": "RUST",
    ".rb": "RUBY",
    ".php": "PHP",
    ".sql": "SQL",
}

table_settings = {
    "vertical_strategy": "lines",    # ya "text" aapke pdf ke hisab se
    "horizontal_strategy": "lines",
    "text_use_text_flow": True,       # ⚡ Yeh words ko aapas mein jodne se rokega
    "text_x_tolerance": 2            # ⚡ Kam tolerance space ko recognize karne mein help karegi
}


def classify_file(file_path: str | Path) -> str:
    """Return the ingestion strategy for a file based on its extension."""
    extension = Path(file_path).suffix.lower()
    if extension in LANGUAGE_BY_EXTENSION or extension in STRUCTURED_EXTENSIONS:
        return "structural"
    if extension == ".pdf":
        return "pdf"
    if extension == ".docx":
        return "docx"
    if extension == ".csv":
        return "csv"
    return "recursive"


def _read_docx(file_path: Path) -> str:
    """Read DOCX text with the standard library (DOCX is a ZIP/XML format)."""
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(file_path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
        if text.strip():
            paragraphs.append(text.strip())
    return "\n\n".join(paragraphs)


def _read_pdf_text(file_path: Path) -> str:
    """Use pypdf as the clean-text fallback for PDFs."""
    if PdfReader is None:
        raise RuntimeError("PDF support requires the local 'pypdf' dependency")
    reader = PdfReader(str(file_path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _table_text(table: Iterable[Iterable[Any]]) -> str:
    rows = []
    for row in table:
        values = [(cell or "").replace("\n", " ").strip() for cell in row]
        if any(values):
            rows.append(" | ".join(values))
    return "\n".join(rows)


def _extract_pdf_with_tables(file_path: Path) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    """Extract page text, table records, and page boundaries from a PDF.

    Keeping the page text separate is important downstream: a retrieval result
    must be able to point a reader to the same page it was generated from.
    """
    try:
        if pdfplumber is None:
            raise RuntimeError("pdfplumber is unavailable")
        pages: List[str] = []
        table_records: List[Dict[str, Any]] = []
        with pdfplumber.open(file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = (page.extract_text() or "").strip()
                pages.append(page_text)
                # Keep the parser output separate from our table records.  The
                # previous implementation appended records to ``tables`` while
                # iterating it, which made PDFs with tables repeatedly process
                # their own derived records and could make an upload appear to
                # hang.
                extracted_tables = page.extract_tables(table_settings=table_settings)
                for table_number, table in enumerate(extracted_tables, start=1):
                    text = _table_text(table)
                    if text:
                        table_records.append({
                            "page_number": page_number,
                            "table_number": table_number,
                            "text": text,
                            "context": page_text,
                        })
        text = "\n\n".join(page for page in pages if page).strip()
        return text or _read_pdf_text(file_path), table_records, pages
    except Exception:
        return _read_pdf_text(file_path), [], []


def _structural_chunks(text: str, extension: str) -> List[str]:
    """Apply a language-aware splitter, preserving source-language boundaries."""
    if extension in LANGUAGE_BY_EXTENSION:
        language = getattr(Language, LANGUAGE_BY_EXTENSION[extension], None)
        if language is not None:
            return RecursiveCharacterTextSplitter.from_language(
                language=language, chunk_size=1_500, chunk_overlap=150
            ).split_text(text)
        # A language unsupported by the installed LangChain version (such as
        # SQL) is still chunked structurally instead of breaking application
        # startup or silently treating it as a PDF.
        return RecursiveCharacterTextSplitter(
            chunk_size=1_500,
            chunk_overlap=150,
            separators=["\n\n", "\n", ";", "}", " ", ""],
            keep_separator=True,
        ).split_text(text)
    if extension in {".md", ".markdown"}:
        documents = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
            strip_headers=False,
        ).split_text(text)
        return [document.page_content for document in documents] or [text]
    if extension in {".html", ".htm"}:
        documents = HTMLHeaderTextSplitter(
            headers_to_split_on=[("h1", "h1"), ("h2", "h2"), ("h3", "h3")]
        ).split_text(text)
        return [document.page_content for document in documents] or [text]
    # XML has no dedicated LangChain language splitter; retain complete element
    # blocks by splitting at closing tags before falling back to recursive text.
    blocks = [block.strip() for block in re.split(r"(?<=</[^>]+>)\s*", text) if block.strip()]
    return blocks or [text]


def _chunk_metadata(text: str, index: int, strategy: str, **metadata: Any) -> Dict[str, Any]:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    return {
        "chunk_index": index,
        "text": normalized,
        "char_count": len(normalized),
        "token_count_estimate": len(normalized) // 4,
        "chunk_hash": hashlib.md5(normalized.lower().encode()).hexdigest(),
        "chunking_strategy": strategy,
        **metadata,
    }


def _csv_chunks(text: str) -> List[Dict[str, Any]]:
    """Create one self-contained, searchable chunk per CSV record.

    A CSV row is a database-like record, not prose. Keeping it intact prevents
    a lookup such as ``tower 17, flat 1101`` from returning its neighbours.
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []

    headers = [header.strip() for header in reader.fieldnames if header]
    chunks = []
    for row_number, raw_row in enumerate(reader, start=2):
        row = {
            header: (raw_row.get(header) or "").strip()
            for header in headers
        }
        if not any(row.values()):
            continue
        # Label every value explicitly. This is both more readable in sources
        # and much more reliable for keyword retrieval than comma-separated text.
        row_text = "\n".join(f"{header}: {row[header]}" for header in headers)
        chunks.append(
            _chunk_metadata(
                row_text,
                len(chunks),
                "csv_rows",
                chunk_role="row",
                row_number=row_number,
                row_data={key.lower(): value for key, value in row.items()},
            )
        )
    return chunks


def route_and_chunk_document(file_path: str | Path) -> Tuple[str, List[Dict[str, Any]], str]:
    """Classify, parse, and chunk a document with a recursive safe fallback.

    Table documents get a parent record containing the complete table and a child
    record for each row. ``parent_chunk_id`` lets retrieval hydrate a matched row
    with the full table later.
    """
    path = Path(file_path)
    file_type = classify_file(path)
    extension = path.suffix.lower()
    try:
        if file_type == "pdf":
            text, tables, pdf_pages = _extract_pdf_with_tables(path)
            # Split each page independently so a chunk never crosses a page
            # boundary and its preview can name an exact page.
            base_chunks = []
            base_chunk_pages = []
            for page_number, page_text in enumerate(pdf_pages, start=1):
                page_chunks = PDF_TEXT_SPLITTER.split_text(page_text)
                base_chunks.extend(page_chunks)
                base_chunk_pages.extend([page_number] * len(page_chunks))
            if not base_chunks:
                base_chunks = PDF_TEXT_SPLITTER.split_text(text)
                base_chunk_pages = [None] * len(base_chunks)
            strategy = "parent_child_tables" if tables else "recursive_character"
        elif file_type == "docx":
            text = _read_docx(path)
            tables = []
            base_chunks = PDF_TEXT_SPLITTER.split_text(text)
            base_chunk_pages = [None] * len(base_chunks)
            strategy = "recursive_character"
        elif file_type == "csv":
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            tables = []
            base_chunks = []
            base_chunk_pages = []
            strategy = "csv_rows"
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            tables = []
            base_chunks = _structural_chunks(text, extension) if file_type == "structural" else PDF_TEXT_SPLITTER.split_text(text)
            base_chunk_pages = [None] * len(base_chunks)
            strategy = "structural" if file_type == "structural" else "recursive_character"
    except Exception:
        # Any unsupported encoding/parser/layout failure still produces useful text.
        text = path.read_text(encoding="utf-8", errors="replace") if extension != ".pdf" else _read_pdf_text(path)
        tables = []
        base_chunks = PDF_TEXT_SPLITTER.split_text(text)
        base_chunk_pages = [None] * len(base_chunks)
        strategy = "recursive_character_fallback"

    if not text.strip():
        raise ValueError("No text extracted from document")

    chunks = _csv_chunks(text) if file_type == "csv" else [
        _chunk_metadata(
            chunk,
            index,
            strategy,
            **({"page_number": page_number} if page_number is not None else {}),
        )
        for index, (chunk, page_number) in enumerate(zip(base_chunks, base_chunk_pages))
        if chunk.strip()
    ]
    for table in tables:
        parent_id = f"table-{table['page_number']}-{table['table_number']}"
        # Page context makes the standalone parent understandable while retaining
        # every table row as one intact structure.
        parent_text = f"Page {table['page_number']} context:\n{table['context']}\n\nTable:\n{table['text']}"
        chunks.append(_chunk_metadata(parent_text, len(chunks), "parent_child_tables", chunk_role="parent", parent_chunk_id=parent_id, page_number=table["page_number"]))
        for row_number, row in enumerate(table["text"].splitlines()):
            chunks.append(_chunk_metadata(row, len(chunks), "parent_child_tables", chunk_role="child", parent_chunk_id=parent_id, row_number=row_number, page_number=table["page_number"]))
    return file_type, chunks, text
