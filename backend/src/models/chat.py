"""Chat history models"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChatMessage(BaseModel):
    """Single chat message"""
    user_id: str
    tenant_id: str
    query: str
    answer: str
    sources: List[str]
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class ChatHistory(BaseModel):
    """Chat history for a user"""
    user_id: str
    tenant_id: str
    messages: List[ChatMessage] = []
    
    
class ChatHistoryRequest(BaseModel):
    """Request to retrieve chat history"""
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    limit: int = 50
