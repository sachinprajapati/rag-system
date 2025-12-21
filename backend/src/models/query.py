from pydantic import BaseModel
from typing import List, Optional

class Query(BaseModel):
    query_text: str
    top_k: Optional[int] = 5

class QueryResponse(BaseModel):
    results: List[str]
    scores: List[float]