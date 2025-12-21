"""Chat history storage service using Redis"""
from typing import List, Optional
import json
from datetime import datetime
from src.db.redis_client import RedisClient
from src.models.chat import ChatMessage, ChatHistory
from src.core.config import settings


class ChatHistoryService:
    """Service for storing and retrieving chat history"""
    
    def __init__(self):
        self.redis = RedisClient(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=1  # Use separate DB for chat history
        )
    
    def _get_key(self, user_id: str, tenant_id: str) -> str:
        """Generate Redis key for user chat history"""
        return f"chat:history:{tenant_id}:{user_id}"
    
    def add_message(self, user_id: str, tenant_id: str, query: str, 
                   answer: str, sources: List[str]) -> None:
        """
        Add a chat message to history.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            query: User query
            answer: System answer
            sources: List of source documents
        """
        message = ChatMessage(
            user_id=user_id,
            tenant_id=tenant_id,
            query=query,
            answer=answer,
            sources=sources,
            timestamp=datetime.utcnow()
        )
        
        key = self._get_key(user_id, tenant_id)
        
        # Get existing history
        history = self.get_history(user_id, tenant_id)
        history.messages.append(message)
        
        # Keep only last 100 messages
        if len(history.messages) > 100:
            history.messages = history.messages[-100:]
        
        # Store as JSON
        self.redis.set(
            key, 
            json.dumps([msg.model_dump(mode='json') for msg in history.messages]),
            ex=86400 * 30  # Expire after 30 days
        )
    
    def get_history(self, user_id: str, tenant_id: str, limit: int = 50) -> ChatHistory:
        """
        Get chat history for a user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            limit: Maximum number of messages to return
            
        Returns:
            ChatHistory object
        """
        key = self._get_key(user_id, tenant_id)
        data = self.redis.get(key)
        
        if not data:
            return ChatHistory(user_id=user_id, tenant_id=tenant_id, messages=[])
        
        # Parse JSON
        messages_data = json.loads(data)
        messages = [ChatMessage(**msg) for msg in messages_data[-limit:]]
        
        return ChatHistory(
            user_id=user_id,
            tenant_id=tenant_id,
            messages=messages
        )
    
    def clear_history(self, user_id: str, tenant_id: str) -> None:
        """Clear chat history for a user"""
        key = self._get_key(user_id, tenant_id)
        self.redis.delete(key)
    
    def get_all_user_histories(self, tenant_id: str) -> List[ChatHistory]:
        """Get all chat histories for a tenant (admin only)"""
        # This is a simplified version
        # In production, use Redis SCAN to iterate over keys
        # For now, return empty list as we don't track all user keys
        return []


# Global instance
_chat_history_service = None


def get_chat_history_service() -> ChatHistoryService:
    """Get or create global chat history service instance"""
    global _chat_history_service
    if _chat_history_service is None:
        _chat_history_service = ChatHistoryService()
    return _chat_history_service
