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
        <div className="App">
            <header className="app-header">
                <div className="brand">
                    <div className="brand-mark">✦</div>
                    <div>
                        <h1>Askwise</h1>
                        <p>AI workspace for your documents</p>
                    </div>
                </div>
                <div className="header-actions">
                    <div className="view-toggle">
                        <button
                            onClick={() => setActiveView('rag')}
                            className={activeView === 'rag' ? 'active' : ''}
                        >
                            Chat
                        </button>
                        <button
                            onClick={() => setActiveView('monitoring')}
                            className={activeView === 'monitoring' ? 'active' : ''}
                        >
                            Monitoring
                        </button>
                    </div>

                    {activeView === 'rag' && (
                        <button
                            onClick={() => setShowSidebar(!showSidebar)}
                            className="icon-button"
                            title={showSidebar ? 'Hide conversations' : 'Show conversations'}
                        >
                            {showSidebar ? '◧' : '▣'}
                        </button>
                    )}
                    <div className="system-status"><span></span> System online</div>
                </div>
            </header>
            
            <div className="workspace">
                {activeView === 'rag' ? (
                    <>
                        {showSidebar && (
                            <Conversations 
                                activeConversationId={activeConversationId}
                                onSelectConversation={setActiveConversationId}
                            />
                        )}
                        
                        <main className="app-content">
                            <DocumentUpload />
                            <QueryInterface 
                                activeConversationId={activeConversationId}
                                onConversationCreated={handleConversationCreated}
                            />
                            <ProcessingStatus isProcessing={false} />
                        </main>
                    </>
                ) : (
                    <main className="app-content">
                        <MonitoringDashboard />
                    </main>
                )}
            </div>
        </div>
    );
};

export default App;
