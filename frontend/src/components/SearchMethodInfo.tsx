import React, { useState } from 'react';

const SearchMethodInfo: React.FC = () => {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div style={{ 
            backgroundColor: '#f0f7ff', 
            border: '1px solid #c3dafe', 
            borderRadius: '8px', 
            padding: '15px',
            marginBottom: '20px'
        }}>
            <div 
                style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    cursor: 'pointer'
                }}
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <h3 style={{ margin: 0, color: '#1e40af' }}>
                    ℹ️ Search Methods Explained
                </h3>
                <span style={{ fontSize: '20px', color: '#1e40af' }}>
                    {isExpanded ? '▼' : '▶'}
                </span>
            </div>

            {isExpanded && (
                <div style={{ marginTop: '15px' }}>
                    <div style={{ marginBottom: '15px' }}>
                        <h4 style={{ margin: '0 0 5px 0', color: '#1e40af' }}>
                            🔀 Hybrid (Recommended) ⭐
                        </h4>
                        <p style={{ margin: '5px 0', fontSize: '14px', lineHeight: '1.6' }}>
                            <strong>Best for most queries.</strong> Combines semantic understanding (vector search) 
                            with exact keyword matching (BM25). Gives you the best of both worlds - understands 
                            meaning while also catching specific terms.
                        </p>
                        <p style={{ margin: '5px 0', fontSize: '13px', color: '#666' }}>
                            <em>Example:</em> "What are the health insurance options?" → Finds semantically 
                            similar content about "medical coverage" while prioritizing exact mentions of "health insurance"
                        </p>
                    </div>

                    <div style={{ marginBottom: '15px' }}>
                        <h4 style={{ margin: '0 0 5px 0', color: '#1e40af' }}>
                            🧠 Vector (Semantic Search)
                        </h4>
                        <p style={{ margin: '5px 0', fontSize: '14px', lineHeight: '1.6' }}>
                            Uses AI embeddings to understand <strong>meaning and context</strong>. Great for 
                            conceptual queries, paraphrasing, and finding related content even if exact words don't match.
                        </p>
                        <p style={{ margin: '5px 0', fontSize: '13px', color: '#666' }}>
                            <em>Example:</em> "Tell me about employee benefits" → Also finds "compensation package", 
                            "perks", "workplace rewards"
                        </p>
                    </div>

                    <div>
                        <h4 style={{ margin: '0 0 5px 0', color: '#1e40af' }}>
                            🔍 Keyword (BM25)
                        </h4>
                        <p style={{ margin: '5px 0', fontSize: '14px', lineHeight: '1.6' }}>
                            Traditional <strong>keyword matching</strong> using the BM25 algorithm. Best for 
                            specific terms, technical jargon, IDs, or when you need exact phrase matches.
                        </p>
                        <p style={{ margin: '5px 0', fontSize: '13px', color: '#666' }}>
                            <em>Example:</em> "ISO 27001 certification" → Prioritizes documents with exact 
                            matches for "ISO 27001"
                        </p>
                    </div>

                    <div style={{ 
                        marginTop: '15px', 
                        padding: '10px', 
                        backgroundColor: '#fef3c7', 
                        borderRadius: '5px',
                        fontSize: '13px'
                    }}>
                        <strong>💡 Pro Tip:</strong> Start with <strong>Hybrid</strong> for balanced results. 
                        Switch to <strong>Vector</strong> for conceptual questions or <strong>Keyword</strong> 
                        for precise technical terms.
                    </div>
                </div>
            )}
        </div>
    );
};

export default SearchMethodInfo;
