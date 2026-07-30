import React, { useEffect, useState } from 'react';
import { getConversation, queryRAGSystem } from '../services/api';

interface QueryResult {
    answer: string;
    retrieved_documents: Array<{ text: string; file_name: string; score: number; search_method?: string }>;
    sources: string[];
    conversation_id?: string;
}

interface Message {
    message_id: string;
    query: string;
    answer: string;
    sources: string[];
    timestamp: string;
}

type SearchMethod = 'vector' | 'keyword' | 'hybrid';

interface QueryInterfaceProps {
    activeConversationId: string | null;
    onConversationCreated?: (conversationId: string) => void;
}

const QueryInterface: React.FC<QueryInterfaceProps> = ({ activeConversationId, onConversationCreated }) => {
    const [query, setQuery] = useState('');
    const [result, setResult] = useState<QueryResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchMethod, setSearchMethod] = useState<SearchMethod>('hybrid');
    const [topK, setTopK] = useState(5);
    const [history, setHistory] = useState<Message[]>([]);
    const [conversationTitle, setConversationTitle] = useState('');

    useEffect(() => {
        const loadConversation = async () => {
            if (!activeConversationId) {
                setHistory([]);
                setConversationTitle('');
                setResult(null);
                return;
            }
            try {
                const conversation = await getConversation(activeConversationId);
                setHistory(conversation.messages || []);
                setConversationTitle(conversation.title || 'Untitled chat');
                setResult(null);
            } catch (err) {
                console.error('Failed to load conversation:', err);
                setHistory([]);
                setConversationTitle('');
            }
        };
        loadConversation();
    }, [activeConversationId]);

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!query.trim() || loading) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await queryRAGSystem(query.trim(), topK, searchMethod, activeConversationId || undefined);
            setResult(data);
            setQuery('');
            const conversationId = data.conversation_id || activeConversationId;
            if (data.conversation_id && !activeConversationId) onConversationCreated?.(data.conversation_id);
            if (conversationId) {
                const conversation = await getConversation(conversationId);
                setHistory(conversation.messages || []);
                setConversationTitle(conversation.title || 'Untitled chat');
            }
        } catch (err: any) {
            console.error('Query error:', err);
            setError(err?.response?.data?.detail || err.message || 'Unable to generate an answer right now.');
        } finally {
            setLoading(false);
        }
    };

    const renderMessage = (message: Message) => (
        <React.Fragment key={message.message_id}>
            <article className="chat-message user-message"><div className="message-avatar">You</div><div className="message-body"><p>{message.query}</p></div></article>
            <article className="chat-message assistant-message"><div className="message-avatar assistant-avatar">AI</div><div className="message-body"><div className="message-label">Askwise</div><p>{message.answer}</p>{message.sources?.length > 0 && <div className="source-pills">{message.sources.map((source) => <span key={source}>⌁ {source}</span>)}</div>}</div></article>
        </React.Fragment>
    );

    return (
        <section className="chat-shell">
            <div className="chat-heading">
                <div>
                    <span className="eyebrow">DOCUMENT INTELLIGENCE</span>
                    <h2>{conversationTitle || 'How can I help you today?'}</h2>
                    <p>{conversationTitle ? 'Continue asking questions about your knowledge base.' : 'Ask anything from your uploaded documents.'}</p>
                </div>
                {activeConversationId && <span className="active-chat-badge">● Active chat</span>}
            </div>

            <div className={`message-stream ${!history.length && !result ? 'empty-stream' : ''}`}>
                {!history.length && !result && <div className="welcome-state"><div className="welcome-orb">✦</div><h3>Ready when you are</h3><p>Upload a document, then ask a focused question to find the answers that matter.</p><div className="prompt-suggestions"><button onClick={() => setQuery('Summarize the key points in my documents')}>Summarize key points</button><button onClick={() => setQuery('What are the most important action items?')}>Find action items</button><button onClick={() => setQuery('What should I know first?')}>What should I know first?</button></div></div>}
                {history.map(renderMessage)}
                {result && <article className="chat-message assistant-message latest-answer"><div className="message-avatar assistant-avatar">AI</div><div className="message-body"><div className="message-label">Askwise <span>{result.retrieved_documents?.[0]?.search_method || searchMethod} search</span></div><p>{result.answer}</p>{result.sources?.length > 0 && <div className="source-pills">{result.sources.map((source) => <span key={source}>⌁ {source}</span>)}</div>}{result.retrieved_documents?.length > 0 && <details className="evidence"><summary>View {result.retrieved_documents.length} retrieved sources</summary>{result.retrieved_documents.map((doc, index) => <div className="evidence-item" key={`${doc.file_name}-${index}`}><strong>{doc.file_name}</strong><span>Match {doc.score?.toFixed(3)}</span><p>{doc.text}</p></div>)}</details>}</div></article>}
                {loading && <article className="chat-message assistant-message"><div className="message-avatar assistant-avatar">AI</div><div className="typing-indicator"><i></i><i></i><i></i></div></article>}
            </div>

            {error && <div className="query-error">{error}</div>}
            <form className="composer" onSubmit={handleSubmit}>
                <textarea value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSubmit(event); } }} placeholder="Message your documents…" rows={1} />
                <div className="composer-footer">
                    <div className="composer-controls">
                        <select value={searchMethod} onChange={(event) => setSearchMethod(event.target.value as SearchMethod)} aria-label="Search method"><option value="hybrid">✦ Hybrid search</option><option value="vector">◎ Semantic search</option><option value="keyword">⌕ Keyword search</option></select>
                        <label>Sources <input type="number" min="1" max="20" value={topK} onChange={(event) => setTopK(Number(event.target.value) || 5)} /></label>
                    </div>
                    <button className="send-button" type="submit" disabled={!query.trim() || loading} aria-label="Send message">↑</button>
                </div>
            </form>
            <p className="composer-disclaimer">Askwise can make mistakes. Verify important information against the source documents.</p>
        </section>
    );
};

export default QueryInterface;
