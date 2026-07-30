"""Chat history storage service using Redis with conversation support"""
from typing import List, Optional
import json
from datetime import datetime
import uuid
from src.db.redis_client import RedisClient
from src.models.chat import (
    ChatMessage, ChatHistory, Conversation, 
    ConversationSummary, CreateConversationRequest
)
from src.core.config import settings


class ChatHistoryService:
    """Service for storing and retrieving chat history with conversations"""
    
    def __init__(self):
        self.redis = RedisClient(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=1  # Use separate DB for chat history
        )
    
    def _get_conversation_key(self, conversation_id: str) -> str:
        """Generate Redis key for a conversation"""
        return f"chat:conversation:{conversation_id}"
    
    def _get_user_conversations_key(self, user_id: str, tenant_id: str) -> str:
        """Generate Redis key for user's conversation list"""
        return f"chat:user_conversations:{tenant_id}:{user_id}"
    
    def _get_key(self, user_id: str, tenant_id: str) -> str:
        """Generate Redis key for user chat history (legacy)"""
        return f"chat:history:{tenant_id}:{user_id}"
    
    def create_conversation(
        self, 
        user_id: str, 
        tenant_id: str,
        title: Optional[str] = None
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            title: Optional conversation title
            
        Returns:
            Created Conversation object
        """
        conversation = Conversation(
            user_id=user_id,
            tenant_id=tenant_id,
            title=title or "New Conversation"
        )
        
        # Store conversation
        conv_key = self._get_conversation_key(conversation.conversation_id)
        self.redis.set(
            conv_key,
            json.dumps(conversation.model_dump(mode='json')),
            ex=86400 * 90  # Expire after 90 days
        )
        
        # Add to user's conversation list
        user_conv_key = self._get_user_conversations_key(user_id, tenant_id)
        conv_list = self.redis.get(user_conv_key)
        
        if conv_list:
            conv_ids = json.loads(conv_list)
        else:
            conv_ids = []
        
        conv_ids.append(conversation.conversation_id)
        self.redis.set(
            user_conv_key,
            json.dumps(conv_ids),
            ex=86400 * 90
        )
        
        return conversation
    
    def add_message(
        self, 
        user_id: str, 
        tenant_id: str, 
        query: str, 
        answer: str, 
        sources: List[str],
        conversation_id: Optional[str] = None,
        search_method: str = "hybrid",
        metadata: Optional[dict] = None
    ) -> ChatMessage:
        """
        Add a chat message to a conversation.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            query: User query
            answer: System answer
            sources: List of source documents
            conversation_id: Optional conversation ID (creates new if None)
            search_method: Search method used
            metadata: Additional metadata
            
        Returns:
            Created ChatMessage object
        """
        # Get or create conversation
        if conversation_id:
            conversation = self.get_conversation(conversation_id, user_id, tenant_id)
            if not conversation:
                # Invalid conversation_id, create new one
                conversation = self.create_conversation(user_id, tenant_id)
        else:
            # Create new conversation
            conversation = self.create_conversation(user_id, tenant_id)
        
        # Create message
        message = ChatMessage(
            conversation_id=conversation.conversation_id,
            user_id=user_id,
            tenant_id=tenant_id,
            query=query,
            answer=answer,
            sources=sources,
            search_method=search_method,
            metadata=metadata or {}
        )
        
        # Add to conversation
        conversation.add_message(message)
        
        # Keep only last 100 messages per conversation
        if len(conversation.messages) > 100:
            conversation.messages = conversation.messages[-100:]
        
        # Store updated conversation
        conv_key = self._get_conversation_key(conversation.conversation_id)
        self.redis.set(
            conv_key,
            json.dumps(conversation.model_dump(mode='json')),
            ex=86400 * 90
        )
        
        return message
    
    def get_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        tenant_id: str
    ) -> Optional[Conversation]:
        """
        Get a specific conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID (for verification)
            tenant_id: Tenant ID (for verification)
            
        Returns:
            Conversation object or None
        """
        conv_key = self._get_conversation_key(conversation_id)
        data = self.redis.get(conv_key)
        
        if not data:
            return None
        
        conversation = Conversation(**json.loads(data))
        
        # Verify ownership
        if conversation.user_id != user_id or conversation.tenant_id != tenant_id:
            return None
        
        return conversation
    
    def list_conversations(
        self, 
        user_id: str, 
        tenant_id: str,
        limit: int = 50
    ) -> List[ConversationSummary]:
        """
        List all conversations for a user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            limit: Maximum number of conversations
            
        Returns:
            List of conversation summaries
        """
        user_conv_key = self._get_user_conversations_key(user_id, tenant_id)
        conv_list = self.redis.get(user_conv_key)
        
        if not conv_list:
            return []
        
        conv_ids = json.loads(conv_list)[-limit:]
        summaries = []
        
        for conv_id in reversed(conv_ids):
            conversation = self.get_conversation(conv_id, user_id, tenant_id)
            if conversation:
                last_query = conversation.messages[-1].query if conversation.messages else None
                summaries.append(ConversationSummary(
                    conversation_id=conversation.conversation_id,
                    title=conversation.title,
                    message_count=len(conversation.messages),
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                    last_query=last_query
                ))
        
        return summaries
    
    def get_history(self, user_id: str, tenant_id: str, limit: int = 50) -> ChatHistory:
        """
        Get complete chat history for a user (all conversations).
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            limit: Maximum number of conversations
            
        Returns:
            ChatHistory object with all conversations
        """
        user_conv_key = self._get_user_conversations_key(user_id, tenant_id)
        conv_list = self.redis.get(user_conv_key)
        
        if not conv_list:
            return ChatHistory(
                user_id=user_id,
                tenant_id=tenant_id,
                conversations=[],
                total_conversations=0,
                total_messages=0
            )
        
        conv_ids = json.loads(conv_list)[-limit:]
        conversations = []
        total_messages = 0
        
        for conv_id in reversed(conv_ids):
            conversation = self.get_conversation(conv_id, user_id, tenant_id)
            if conversation:
                conversations.append(conversation)
                total_messages += len(conversation.messages)
        
        return ChatHistory(
            user_id=user_id,
            tenant_id=tenant_id,
            conversations=conversations,
            total_conversations=len(conversations),
            total_messages=total_messages
        )
    
    def delete_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        tenant_id: str
    ) -> bool:
        """
        Delete a specific conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID (for verification)
            tenant_id: Tenant ID (for verification)
            
        Returns:
            True if deleted, False if not found/unauthorized
        """
        # Verify ownership first
        conversation = self.get_conversation(conversation_id, user_id, tenant_id)
        if not conversation:
            return False
        
        # Delete conversation
        conv_key = self._get_conversation_key(conversation_id)
        self.redis.delete(conv_key)
        
        # Remove from user's conversation list
        user_conv_key = self._get_user_conversations_key(user_id, tenant_id)
        conv_list = self.redis.get(user_conv_key)
        
        if conv_list:
            conv_ids = json.loads(conv_list)
            if conversation_id in conv_ids:
                conv_ids.remove(conversation_id)
                self.redis.set(
                    user_conv_key,
                    json.dumps(conv_ids),
                    ex=86400 * 90
                )
        
        return True
    
    def clear_history(self, user_id: str, tenant_id: str) -> None:
        """
        Clear all chat history for a user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
        """
        # Get all conversation IDs
        user_conv_key = self._get_user_conversations_key(user_id, tenant_id)
        conv_list = self.redis.get(user_conv_key)
        
        if conv_list:
            conv_ids = json.loads(conv_list)
            # Delete each conversation
            for conv_id in conv_ids:
                conv_key = self._get_conversation_key(conv_id)
                self.redis.delete(conv_key)
        
        # Delete user's conversation list
        self.redis.delete(user_conv_key)
        
        # Also delete legacy format
        legacy_key = self._get_key(user_id, tenant_id)
        self.redis.delete(legacy_key)
    
    def update_conversation_title(
        self,
        conversation_id: str,
        user_id: str,
        tenant_id: str,
        new_title: str
    ) -> bool:
        """
        Update conversation title.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID (for verification)
            tenant_id: Tenant ID (for verification)
            new_title: New title
            
        Returns:
            True if updated, False if not found/unauthorized
        """
        conversation = self.get_conversation(conversation_id, user_id, tenant_id)
        if not conversation:
            return False
        
        conversation.title = new_title
        conversation.updated_at = datetime.utcnow()
        
        conv_key = self._get_conversation_key(conversation_id)
        self.redis.set(
            conv_key,
            json.dumps(conversation.model_dump(mode='json')),
            ex=86400 * 90
        )
        
        return True


# Global instance
_chat_history_service = None


def get_chat_history_service() -> ChatHistoryService:
    """Get or create global chat history service instance"""
    global _chat_history_service
    if _chat_history_service is None:
        _chat_history_service = ChatHistoryService()
    return _chat_history_service
