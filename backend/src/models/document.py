from pydantic import BaseModel
from typing import List, Optional

class Document(BaseModel):
    id: str
    title: str
    content: str
    metadata: Optional[dict] = None

class DocumentInDB(Document):
    embeddings: List[float] = []