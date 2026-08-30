import React, { useEffect, useMemo, useState } from 'react';
import { deleteConversation, listConversations, updateConversationTitle } from '../services/api';

interface ConversationSummary { conversation_id: string; title: string; message_count: number; updated_at: string; }
interface Folder { id: string; name: string; }
interface SidebarPreferences { pinnedIds: string[]; folders: Folder[]; folderByConversation: Record<string, string>; }
interface ConversationsProps { activeConversationId: string | null; onSelectConversation: (conversationId: string | null) => void; }

const preferencesKey = 'askwise-conversation-organization';
const emptyPreferences: SidebarPreferences = { pinnedIds: [], folders: [], folderByConversation: {} };
const readPreferences = (): SidebarPreferences => {
    try {
        const saved = localStorage.getItem(preferencesKey);
        if (!saved) return emptyPreferences;
        const parsed = JSON.parse(saved);
        return { pinnedIds: Array.isArray(parsed.pinnedIds) ? parsed.pinnedIds : [], folders: Array.isArray(parsed.folders) ? parsed.folders : [], folderByConversation: parsed.folderByConversation || {} };
    } catch { return emptyPreferences; }
};

const Conversations: React.FC<ConversationsProps> = ({ activeConversationId, onSelectConversation }) => {
    const [conversations, setConversations] = useState<ConversationSummary[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState('');
    const [query, setQuery] = useState('');
    const [preferences, setPreferences] = useState<SidebarPreferences>(readPreferences);
    const [newFolderName, setNewFolderName] = useState('');
    const [addingFolder, setAddingFolder] = useState(false);
    const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({});

    const persistPreferences = (next: SidebarPreferences) => { setPreferences(next); localStorage.setItem(preferencesKey, JSON.stringify(next)); };
    const loadConversations = async () => {
        try { setLoading(true); const data = await listConversations(); setConversations(data.conversations || []); setError(null); }
        catch (err) { console.error('Failed to load conversations:', err); setError('Could not load conversations'); }
        finally { setLoading(false); }
    };
    useEffect(() => { loadConversations(); }, []);
    useEffect(() => { if (activeConversationId) loadConversations(); }, [activeConversationId]);

    // A conversation is created only after the first prompt succeeds. Resetting
    // the active ID gives the composer a fresh state without saving an empty chat.
    const handleNewConversation = () => onSelectConversation(null);
    const handleDelete = async (conversationId: string, event: React.MouseEvent) => {
        event.stopPropagation(); if (!confirm('Delete this conversation?')) return;
        try {
            await deleteConversation(conversationId); if (activeConversationId === conversationId) onSelectConversation(null);
            const { [conversationId]: removed, ...folderByConversation } = preferences.folderByConversation;
            persistPreferences({ ...preferences, pinnedIds: preferences.pinnedIds.filter((id) => id !== conversationId), folderByConversation }); await loadConversations();
        } catch (err) { console.error('Failed to delete conversation:', err); setError('Could not delete conversation'); }
    };
    const saveTitle = async (conversationId: string) => {
        if (!editTitle.trim()) return;
        try { await updateConversationTitle(conversationId, editTitle.trim()); setEditingId(null); await loadConversations(); }
        catch (err) { console.error('Failed to rename conversation:', err); setError('Could not rename conversation'); }
    };
    const addFolder = () => {
        const name = newFolderName.trim(); if (!name) return;
        persistPreferences({ ...preferences, folders: [...preferences.folders, { id: crypto.randomUUID(), name }] }); setNewFolderName(''); setAddingFolder(false);
    };
    const deleteFolder = (folderId: string, event: React.MouseEvent) => {
        event.stopPropagation(); const folderByConversation = Object.fromEntries(Object.entries(preferences.folderByConversation).filter(([, id]) => id !== folderId));
        persistPreferences({ ...preferences, folders: preferences.folders.filter((folder) => folder.id !== folderId), folderByConversation });
    };
    const togglePin = (conversationId: string, event: React.MouseEvent) => {
        event.stopPropagation(); const isPinned = preferences.pinnedIds.includes(conversationId);
        persistPreferences({ ...preferences, pinnedIds: isPinned ? preferences.pinnedIds.filter((id) => id !== conversationId) : [...preferences.pinnedIds, conversationId] });
    };
    const moveToFolder = (conversationId: string, folderId: string) => {
        const next = { ...preferences.folderByConversation }; if (folderId) next[conversationId] = folderId; else delete next[conversationId];
        persistPreferences({ ...preferences, folderByConversation: next });
    };
    const relativeDate = (value: string) => { const minutes = Math.floor((Date.now() - new Date(value).getTime()) / 60000); if (minutes < 1) return 'Now'; if (minutes < 60) return `${minutes}m`; if (minutes < 1440) return `${Math.floor(minutes / 60)}h`; return `${Math.floor(minutes / 1440)}d`; };
    const visible = useMemo(() => conversations.filter((conversation) => conversation.title.toLowerCase().includes(query.trim().toLowerCase())), [conversations, query]);
    const pinned = visible.filter((conversation) => preferences.pinnedIds.includes(conversation.conversation_id));
    const uncategorized = visible.filter((conversation) => !preferences.folderByConversation[conversation.conversation_id] && !preferences.pinnedIds.includes(conversation.conversation_id));

    const ConversationItem = ({ conversation }: { conversation: ConversationSummary }) => {
        const isPinned = preferences.pinnedIds.includes(conversation.conversation_id);
        const isSelected = activeConversationId === conversation.conversation_id;
        return <div className={`conversation-item ${isSelected ? 'selected' : ''}`}>
            {editingId === conversation.conversation_id ? <div className="conversation-editor"><input autoFocus value={editTitle} onChange={(event) => setEditTitle(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') saveTitle(conversation.conversation_id); if (event.key === 'Escape') setEditingId(null); }} /><button onClick={() => saveTitle(conversation.conversation_id)}>Save</button><button onClick={() => setEditingId(null)}>Cancel</button></div> : <>
                <div className="conversation-row"><button className="conversation-select" onClick={() => onSelectConversation(conversation.conversation_id)} aria-current={isSelected ? 'page' : undefined}><span className="conversation-title">{conversation.title}</span><span className="conversation-meta">{conversation.message_count} messages · {relativeDate(conversation.updated_at)}</span></button><div className="conversation-actions"><button className={isPinned ? 'is-pinned' : ''} title={isPinned ? 'Unpin chat' : 'Pin chat'} aria-label={isPinned ? 'Unpin chat' : 'Pin chat'} onClick={(event) => togglePin(conversation.conversation_id, event)}>⌖</button><button title="Rename" aria-label="Rename chat" onClick={(event) => { event.stopPropagation(); setEditingId(conversation.conversation_id); setEditTitle(conversation.title); }}>✎</button><button title="Delete" aria-label="Delete chat" onClick={(event) => handleDelete(conversation.conversation_id, event)}>×</button></div></div>
                <div className="conversation-subrow"><select aria-label={`Move ${conversation.title} to a folder`} value={preferences.folderByConversation[conversation.conversation_id] || ''} onChange={(event) => moveToFolder(conversation.conversation_id, event.target.value)}><option value="">No folder</option>{preferences.folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}</select></div>
            </>}
        </div>;
    };

    return <aside className="conversation-sidebar" id="conversation-sidebar" aria-label="Conversations">
        <button className="new-chat-button" onClick={handleNewConversation}><span>＋</span> New chat</button>
        <label className="conversation-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search chats" aria-label="Search chats" />{query && <button onClick={() => setQuery('')} aria-label="Clear search">×</button>}</label>
        {loading && <div className="sidebar-state">Loading chats…</div>}{error && <div className="sidebar-error">{error}</div>}
        <div className="conversation-list">
            {!!pinned.length && <section className="conversation-section"><div className="sidebar-label section-label">Pinned <span>{pinned.length}</span></div>{pinned.map((conversation) => <ConversationItem key={conversation.conversation_id} conversation={conversation} />)}</section>}
            <section className="conversation-section"><div className="sidebar-label section-label">Folders <button onClick={() => setAddingFolder(true)} title="Create folder" aria-label="Create folder">＋</button></div>{addingFolder && <div className="folder-editor"><input autoFocus placeholder="Folder name" value={newFolderName} onChange={(event) => setNewFolderName(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') addFolder(); if (event.key === 'Escape') setAddingFolder(false); }} /><button onClick={addFolder}>Add</button></div>}
                {preferences.folders.map((folder) => { const chats = visible.filter((conversation) => preferences.folderByConversation[conversation.conversation_id] === folder.id); const open = openFolders[folder.id] !== false; return <div className="folder-group" key={folder.id}><div className="folder-heading"><button className="folder-toggle" onClick={() => setOpenFolders({ ...openFolders, [folder.id]: !open })} aria-expanded={open}><span>{open ? '⌄' : '›'}</span>▱ {folder.name}<small>{chats.length}</small></button><button className="folder-delete" title={`Delete ${folder.name} folder`} onClick={(event) => deleteFolder(folder.id, event)}>×</button></div>{open && chats.map((conversation) => <ConversationItem key={conversation.conversation_id} conversation={conversation} />)}</div>; })}
            </section>
            {!!uncategorized.length && <section className="conversation-section"><div className="sidebar-label section-label">All chats</div>{uncategorized.map((conversation) => <ConversationItem key={conversation.conversation_id} conversation={conversation} />)}</section>}
            {!loading && !conversations.length && !error && <div className="sidebar-empty"><div>◌</div>Start a chat to explore your documents.</div>}
            {!loading && !!conversations.length && !visible.length && <div className="sidebar-empty"><div>⌕</div>No chats match “{query}”.</div>}
        </div><div className="sidebar-footer"><span>⌘</span> Askwise RAG</div>
    </aside>;
};
export default Conversations;
