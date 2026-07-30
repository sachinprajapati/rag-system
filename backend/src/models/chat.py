"""Chat history models with conversation support"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class ChatMessage(BaseModel):
    """Single chat message in a conversation"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    user_id: str
    tenant_id: str
    query: str
    answer: str
    sources: List[str] = []
    search_method: Optional[str] = "hybrid"
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    """A conversation thread"""
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    tenant_id: str
    title: Optional[str] = "New Conversation"
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}
    
    def add_message(self, message: ChatMessage):
        """Add a message to the conversation"""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        # Auto-generate title from first query
        if len(self.messages) == 1 and self.title == "New Conversation":
            self.title = message.query[:50] + ("..." if len(message.query) > 50 else "")


class ChatHistory(BaseModel):
    """Chat history for a user with multiple conversations"""
    user_id: str
    tenant_id: str
    conversations: List[Conversation] = []
    total_conversations: int = 0
    total_messages: int = 0


class ConversationSummary(BaseModel):
    """Summary of a conversation"""
    conversation_id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_query: Optional[str] = None


class ChatHistoryRequest(BaseModel):
    """Request to retrieve chat history"""
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    conversation_id: Optional[str] = None
    limit: int = 50


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    title: Optional[str] = "New Conversation"
    metadata: Dict[str, Any] = {}
