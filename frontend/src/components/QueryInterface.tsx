import React, { useState } from 'react';
import { queryRAGSystem } from '../services/api';
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
}

type SearchMethod = 'vector' | 'keyword' | 'hybrid';

const QueryInterface: React.FC = () => {
    const [query, setQuery] = useState('');
    const [result, setResult] = useState<QueryResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchMethod, setSearchMethod] = useState<SearchMethod>('hybrid');
    const [topK, setTopK] = useState(5);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const data = await queryRAGSystem(query, topK, searchMethod);
            console.log('Query result:', data);
            setResult(data);
        } catch (err: any) {
            console.error('Query error:', err);
            setError(err?.response?.data?.detail || err.message || 'Failed to query');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card">
            <h2>Query the RAG System</h2>
            
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