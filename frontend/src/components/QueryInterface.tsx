import React, { useState, useEffect } from 'react';
import { queryRAGSystem, getConversation } from '../services/api';
import SearchMethodInfo from './SearchMethodInfo';

interface QueryResult {
    query: string;
    answer: string;
    retrieved_documents: Array<{
        text: string;
        file_name: string;
        score: number;
        search_method?: string;
    }>;
    sources: string[];
    conversation_id?: string;
}

interface Message {
    message_id: string;
    conversation_id: string;
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
    const [conversationHistory, setConversationHistory] = useState<Message[]>([]);
    const [conversationTitle, setConversationTitle] = useState<string>('');

    // Load conversation history when active conversation changes
    useEffect(() => {
        const loadConversation = async () => {
            if (activeConversationId) {
                try {
                    const conv = await getConversation(activeConversationId);
                    setConversationHistory(conv.messages || []);
                    setConversationTitle(conv.title);
                    setResult(null); // Clear current result when switching conversations
                } catch (err) {
                    console.error('Failed to load conversation:', err);
                    setConversationHistory([]);
                    setConversationTitle('');
                }
            } else {
                setConversationHistory([]);
                setConversationTitle('');
                setResult(null);
            }
        };
        loadConversation();
    }, [activeConversationId]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const data = await queryRAGSystem(query, topK, searchMethod, activeConversationId || undefined);
            console.log('Query result:', data);
            setResult(data);
            
            // If a new conversation was created, notify parent and load its history
            if (data.conversation_id && !activeConversationId && onConversationCreated) {
                onConversationCreated(data.conversation_id);
                // Load the newly created conversation's history
                try {
                    const conv = await getConversation(data.conversation_id);
                    setConversationHistory(conv.messages || []);
                    setConversationTitle(conv.title);
                } catch (err) {
                    console.error('Failed to load new conversation:', err);
                }
            } else if (activeConversationId) {
                // Reload conversation history if we're in an existing conversation
                const conv = await getConversation(activeConversationId);
                setConversationHistory(conv.messages || []);
            }
            
            setQuery(''); // Clear input after successful query
        } catch (err: any) {
            console.error('Query error:', err);
            setError(err?.response?.data?.detail || err.message || 'Failed to query');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <h2>{conversationTitle || 'Query the RAG System'}</h2>
                {activeConversationId && (
                    <span style={{ fontSize: '12px', color: '#666', backgroundColor: '#e0e0e0', padding: '4px 8px', borderRadius: '4px' }}>
                        💬 Conversation Active
                    </span>
                )}
            </div>
            
            {/* Display conversation history */}
            {conversationHistory.length > 0 && (
                <div style={{ 
                    marginBottom: '20px', 
                    maxHeight: '300px', 
                    overflowY: 'auto',
                    border: '1px solid #ddd',
                    borderRadius: '5px',
                    padding: '10px',
                    backgroundColor: '#fafafa'
                }}>
                    <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#666' }}>Previous Messages:</h3>
                    {conversationHistory.map((msg, index) => (
                        <div key={msg.message_id} style={{ 
                            marginBottom: '15px', 
                            paddingBottom: '15px', 
                            borderBottom: index < conversationHistory.length - 1 ? '1px solid #e0e0e0' : 'none' 
                        }}>
                            <div style={{ marginBottom: '8px' }}>
                                <strong style={{ color: '#1976d2' }}>Q:</strong> {msg.query}
                                <span style={{ fontSize: '10px', color: '#999', marginLeft: '10px' }}>
                                    {new Date(msg.timestamp).toLocaleString()}
                                </span>
                            </div>
                            <div style={{ paddingLeft: '20px', color: '#555' }}>
                                <strong style={{ color: '#388e3c' }}>A:</strong> {msg.answer}
                            </div>
                        </div>
                    ))}
                </div>
            )}
            
            <SearchMethodInfo />
            
            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    className="input"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask a question about your documents"
                    required
                />
                
                <div style={{ marginTop: '15px', display: 'flex', gap: '20px', alignItems: 'center' }}>
                    <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                            Search Method:
                        </label>
                        <select 
                            className="input"
                            value={searchMethod}
                            onChange={(e) => setSearchMethod(e.target.value as SearchMethod)}
                            style={{ width: '100%' }}
                        >
                            <option value="hybrid">🔀 Hybrid (Recommended)</option>
                            <option value="vector">🧠 Vector (Semantic)</option>
                            <option value="keyword">🔍 Keyword (BM25)</option>
                        </select>
                        <small style={{ color: '#666', fontSize: '12px' }}>
                            {searchMethod === 'hybrid' && '✨ Combines semantic understanding + exact keyword matching'}
                            {searchMethod === 'vector' && '🎯 Best for conceptual queries and paraphrasing'}
                            {searchMethod === 'keyword' && '📝 Best for specific terms and exact matches'}
                        </small>
                    </div>
                    
                    <div style={{ width: '120px' }}>
                        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                            Results (Top-K):
                        </label>
                        <input
                            type="number"
                            className="input"
                            value={topK}
                            onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                            min="1"
                            max="20"
                            style={{ width: '100%' }}
                        />
                    </div>
                </div>
                
                <button type="submit" className="button" disabled={loading} style={{ marginTop: '15px' }}>
                    {loading ? 'Processing...' : 'Submit Query'}
                </button>
            </form>

            {error && <div style={{ color: 'red', marginTop: '10px' }}>Error: {error}</div>}

            {result && (
                <div style={{ marginTop: '20px' }}>
                    <div style={{ backgroundColor: '#f5f5f5', padding: '15px', borderRadius: '5px', marginBottom: '15px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                            <h3 style={{ margin: 0 }}>Answer:</h3>
                            <span style={{ fontSize: '12px', color: '#666', backgroundColor: '#e0e0e0', padding: '4px 8px', borderRadius: '4px' }}>
                                {result.retrieved_documents?.[0]?.search_method || searchMethod} search
                            </span>
                        </div>
                        <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{result.answer}</p>
                    </div>

                    {result.retrieved_documents && result.retrieved_documents.length > 0 && (
                        <div>
                            <h3>Retrieved Documents ({result.retrieved_documents.length}):</h3>
                            {result.retrieved_documents.map((doc, index) => (
                                <div key={index} style={{ backgroundColor: '#fff', border: '1px solid #ddd', padding: '10px', marginBottom: '10px', borderRadius: '5px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                                        <strong>{doc.file_name}</strong>
                                        <span style={{ color: '#666' }}>Score: {doc.score?.toFixed(3)}</span>
                                    </div>
                                    <p style={{ margin: '5px 0', fontSize: '14px', color: '#555' }}>{doc.text}</p>
                                </div>
                            ))}
                        </div>
                    )}

                    {result.sources && result.sources.length > 0 && (
                        <div style={{ marginTop: '10px' }}>
                            <strong>Sources:</strong> {result.sources.join(', ')}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default QueryInterface;