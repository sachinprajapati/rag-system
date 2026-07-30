import React, { useState, useEffect } from 'react';
import { listConversations, createConversation, deleteConversation, updateConversationTitle } from '../services/api';

interface ConversationSummary {
    conversation_id: string;
    title: string;
    message_count: number;
    created_at: string;
    updated_at: string;
    last_query?: string;
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
        } catch (err: any) {
            console.error('Failed to load conversations:', err);
            setError('Failed to load conversations');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadConversations();
    }, []);

    // Reload conversations when active conversation changes (e.g., new conversation created)
    useEffect(() => {
        if (activeConversationId) {
            loadConversations();
        }
    }, [activeConversationId]);

    const handleNewConversation = async () => {
        try {
            await createConversation();
            onSelectConversation(null); // Start new conversation
            loadConversations();
        } catch (err: any) {
            console.error('Failed to create conversation:', err);
        }
    };

    const handleDeleteConversation = async (conversationId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm('Delete this conversation?')) return;

        try {
            await deleteConversation(conversationId);
            if (activeConversationId === conversationId) {
                onSelectConversation(null);
            }
            loadConversations();
        } catch (err: any) {
            console.error('Failed to delete conversation:', err);
        }
    };

    const handleStartEdit = (conv: ConversationSummary, e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingId(conv.conversation_id);
        setEditTitle(conv.title);
    };

    const handleSaveEdit = async (conversationId: string) => {
        if (!editTitle.trim()) return;

        try {
            await updateConversationTitle(conversationId, editTitle);
            setEditingId(null);
            loadConversations();
        } catch (err: any) {
            console.error('Failed to update title:', err);
        }
    };

    const handleCancelEdit = () => {
        setEditingId(null);
        setEditTitle('');
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    return (
        <div style={{
            width: '300px',
            borderRight: '1px solid #ddd',
            padding: '20px',
            overflowY: 'auto',
            backgroundColor: '#f9f9f9'
        }}>
            <div style={{ marginBottom: '20px' }}>
                <h3 style={{ margin: '0 0 15px 0' }}>💬 Conversations</h3>
                <button
                    onClick={handleNewConversation}
                    className="button"
                    style={{ width: '100%', padding: '10px' }}
                >
                    + New Conversation
                </button>
            </div>

            {loading && <div style={{ textAlign: 'center', color: '#666' }}>Loading...</div>}
            {error && <div style={{ color: 'red', fontSize: '14px' }}>{error}</div>}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {conversations.map((conv) => (
                    <div
                        key={conv.conversation_id}
                        onClick={() => onSelectConversation(conv.conversation_id)}
                        style={{
                            padding: '12px',
                            backgroundColor: activeConversationId === conv.conversation_id ? '#e3f2fd' : 'white',
                            border: '1px solid #ddd',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            position: 'relative'
                        }}
                        onMouseEnter={(e) => {
                            if (activeConversationId !== conv.conversation_id) {
                                e.currentTarget.style.backgroundColor = '#f5f5f5';
                            }
                        }}
                        onMouseLeave={(e) => {
                            if (activeConversationId !== conv.conversation_id) {
                                e.currentTarget.style.backgroundColor = 'white';
                            }
                        }}
                    >
                        {editingId === conv.conversation_id ? (
                            <div onClick={(e) => e.stopPropagation()}>
                                <input
                                    type="text"
                                    value={editTitle}
                                    onChange={(e) => setEditTitle(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') handleSaveEdit(conv.conversation_id);
                                        if (e.key === 'Escape') handleCancelEdit();
                                    }}
                                    autoFocus
                                    style={{
                                        width: '100%',
                                        padding: '4px',
                                        fontSize: '14px',
                                        border: '1px solid #ccc',
                                        borderRadius: '4px'
                                    }}
                                />
                                <div style={{ marginTop: '5px', display: 'flex', gap: '5px' }}>
                                    <button
                                        onClick={() => handleSaveEdit(conv.conversation_id)}
                                        style={{ padding: '2px 8px', fontSize: '12px' }}
                                    >
                                        Save
                                    </button>
                                    <button
                                        onClick={handleCancelEdit}
                                        style={{ padding: '2px 8px', fontSize: '12px' }}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <>
                                <div style={{
                                    fontWeight: activeConversationId === conv.conversation_id ? 'bold' : 'normal',
                                    fontSize: '14px',
                                    marginBottom: '5px',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap'
                                }}>
                                    {conv.title}
                                </div>
                                <div style={{
                                    fontSize: '12px',
                                    color: '#666',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center'
                                }}>
                                    <span>{conv.message_count} messages</span>
                                    <span>{formatDate(conv.updated_at)}</span>
                                </div>
                                <div style={{
                                    position: 'absolute',
                                    top: '8px',
                                    right: '8px',
                                    display: 'flex',
                                    gap: '5px',
                                    opacity: 0.6
                                }}
                                    onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                                    onMouseLeave={(e) => e.currentTarget.style.opacity = '0.6'}
                                >
                                    <button
                                        onClick={(e) => handleStartEdit(conv, e)}
                                        style={{
                                            padding: '2px 6px',
                                            fontSize: '12px',
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer'
                                        }}
                                        title="Rename"
                                    >
                                        ✏️
                                    </button>
                                    <button
                                        onClick={(e) => handleDeleteConversation(conv.conversation_id, e)}
                                        style={{
                                            padding: '2px 6px',
                                            fontSize: '12px',
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            color: 'red'
                                        }}
                                        title="Delete"
                                    >
                                        🗑️
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                ))}

                {conversations.length === 0 && !loading && (
                    <div style={{ textAlign: 'center', color: '#999', marginTop: '20px', fontSize: '14px' }}>
                        No conversations yet.<br />
                        Start a new one!
                    </div>
                )}
            </div>
        </div>
    );
};

export default Conversations;
