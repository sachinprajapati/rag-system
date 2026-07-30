import React, { useEffect, useState } from 'react';
import { createConversation, deleteConversation, listConversations, updateConversationTitle } from '../services/api';

interface ConversationSummary {
    conversation_id: string;
    title: string;
    message_count: number;
    updated_at: string;
}

interface ConversationsProps {
    activeConversationId: string | null;
    onSelectConversation: (conversationId: string | null) => void;
}

const Conversations: React.FC<ConversationsProps> = ({ activeConversationId, onSelectConversation }) => {
    const [conversations, setConversations] = useState<ConversationSummary[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState('');

    const loadConversations = async () => {
        try {
            setLoading(true);
            const data = await listConversations();
            setConversations(data.conversations || []);
            setError(null);
        } catch (err) {
            console.error('Failed to load conversations:', err);
            setError('Could not load conversations');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadConversations(); }, []);
    useEffect(() => { if (activeConversationId) loadConversations(); }, [activeConversationId]);

    const handleNewConversation = async () => {
        try {
            const conversation = await createConversation();
            onSelectConversation(conversation.conversation_id || null);
            await loadConversations();
        } catch (err) {
            console.error('Failed to create conversation:', err);
            setError('Could not create a new conversation');
        }
    };

    const handleDelete = async (conversationId: string, event: React.MouseEvent) => {
        event.stopPropagation();
        if (!confirm('Delete this conversation?')) return;
        try {
            await deleteConversation(conversationId);
            if (activeConversationId === conversationId) onSelectConversation(null);
            await loadConversations();
        } catch (err) {
            console.error('Failed to delete conversation:', err);
            setError('Could not delete conversation');
        }
    };

    const saveTitle = async (conversationId: string) => {
        if (!editTitle.trim()) return;
        try {
            await updateConversationTitle(conversationId, editTitle.trim());
            setEditingId(null);
            await loadConversations();
        } catch (err) {
            console.error('Failed to rename conversation:', err);
            setError('Could not rename conversation');
        }
    };

    const relativeDate = (value: string) => {
        const minutes = Math.floor((Date.now() - new Date(value).getTime()) / 60000);
        if (minutes < 1) return 'Now';
        if (minutes < 60) return `${minutes}m`;
        if (minutes < 1440) return `${Math.floor(minutes / 60)}h`;
        return `${Math.floor(minutes / 1440)}d`;
    };

    return (
        <aside className="conversation-sidebar">
            <button className="new-chat-button" onClick={handleNewConversation}>
                <span>＋</span> New chat
            </button>
            <div className="sidebar-label">Your conversations</div>
            {loading && <div className="sidebar-state">Loading chats…</div>}
            {error && <div className="sidebar-error">{error}</div>}
            <div className="conversation-list">
                {conversations.map((conversation) => (
                    <div
                        className={`conversation-item ${activeConversationId === conversation.conversation_id ? 'selected' : ''}`}
                        key={conversation.conversation_id}
                        onClick={() => onSelectConversation(conversation.conversation_id)}
                    >
                        {editingId === conversation.conversation_id ? (
                            <div className="conversation-editor" onClick={(event) => event.stopPropagation()}>
                                <input
                                    autoFocus
                                    value={editTitle}
                                    onChange={(event) => setEditTitle(event.target.value)}
                                    onKeyDown={(event) => {
                                        if (event.key === 'Enter') saveTitle(conversation.conversation_id);
                                        if (event.key === 'Escape') setEditingId(null);
                                    }}
                                />
                                <button onClick={() => saveTitle(conversation.conversation_id)}>Save</button>
                                <button onClick={() => setEditingId(null)}>Cancel</button>
                            </div>
                        ) : (
                            <>
                                <div className="conversation-row">
                                    <span className="conversation-title">{conversation.title}</span>
                                    <div className="conversation-actions">
                                        <button title="Rename" onClick={(event) => { event.stopPropagation(); setEditingId(conversation.conversation_id); setEditTitle(conversation.title); }}>✎</button>
                                        <button title="Delete" onClick={(event) => handleDelete(conversation.conversation_id, event)}>×</button>
                                    </div>
                                </div>
                                <span className="conversation-meta">{conversation.message_count} messages · {relativeDate(conversation.updated_at)}</span>
                            </>
                        )}
                    </div>
                ))}
                {!loading && !conversations.length && !error && (
                    <div className="sidebar-empty"><div>◌</div>Start a chat to explore your documents.</div>
                )}
            </div>
            <div className="sidebar-footer"><span>⌘</span> Askwise RAG</div>
        </aside>
    );
};

export default Conversations;
