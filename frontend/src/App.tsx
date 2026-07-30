import React, { useState } from 'react';
import DocumentUpload from './components/DocumentUpload';
import QueryInterface from './components/QueryInterface';
import ProcessingStatus from './components/ProcessingStatus';
import Conversations from './components/Conversations';
import MonitoringDashboard from './components/MonitoringDashboard';

const App: React.FC = () => {
    const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
    const [showSidebar, setShowSidebar] = useState(true);
    const [activeView, setActiveView] = useState<'rag' | 'monitoring'>('rag');

    const handleConversationCreated = (conversationId: string) => {
        // When a new conversation is created from a query, switch to it
        setActiveConversationId(conversationId);
    };

    return (
        <div className="App" style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
            <header className="app-header">
                <div>
                    <h1>RAG System</h1>
                    <p style={{ color: '#fff', margin: 0 }}>Production-Grade RAG System with RBAC & Conversations</p>
                </div>
                <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                    {/* View Toggle */}
                    <div style={{ display: 'flex', gap: '5px', backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: '6px', padding: '4px' }}>
                        <button
                            onClick={() => setActiveView('rag')}
                            style={{
                                padding: '6px 14px',
                                fontSize: '14px',
                                backgroundColor: activeView === 'rag' ? '#fff' : 'transparent',
                                color: activeView === 'rag' ? '#333' : '#fff',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontWeight: activeView === 'rag' ? 'bold' : 'normal'
                            }}
                        >
                            💬 RAG System
                        </button>
                        <button
                            onClick={() => setActiveView('monitoring')}
                            style={{
                                padding: '6px 14px',
                                fontSize: '14px',
                                backgroundColor: activeView === 'monitoring' ? '#fff' : 'transparent',
                                color: activeView === 'monitoring' ? '#333' : '#fff',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontWeight: activeView === 'monitoring' ? 'bold' : 'normal'
                            }}
                        >
                            📊 Monitoring
                        </button>
                    </div>

                    {activeView === 'rag' && (
                        <button
                            onClick={() => setShowSidebar(!showSidebar)}
                            style={{
                                padding: '8px 12px',
                                fontSize: '14px',
                                backgroundColor: '#fff',
                                color: '#333',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer'
                            }}
                        >
                            {showSidebar ? '⬅️ Hide' : '➡️ Show'} Conversations
                        </button>
                    )}
                    <div style={{ color: 'white', fontSize: '0.9rem' }}>
                        🔓 Auth: Disabled | RBAC Ready
                    </div>
                </div>
            </header>
            
            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                {activeView === 'rag' ? (
                    <>
                        {showSidebar && (
                            <Conversations 
                                activeConversationId={activeConversationId}
                                onSelectConversation={setActiveConversationId}
                            />
                        )}
                        
                        <main className="app-content" style={{ flex: 1, overflowY: 'auto' }}>
                            <DocumentUpload />
                            <QueryInterface 
                                activeConversationId={activeConversationId}
                                onConversationCreated={handleConversationCreated}
                            />
                            <ProcessingStatus isProcessing={false} />
                        </main>
                    </>
                ) : (
                    <main className="app-content" style={{ flex: 1, overflowY: 'auto' }}>
                        <MonitoringDashboard />
                    </main>
                )}
            </div>
        </div>
    );
};

export default App;

