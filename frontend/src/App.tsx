import React, { useEffect, useState } from 'react';
import DocumentUpload from './components/DocumentUpload';
import QueryInterface from './components/QueryInterface';
import ProcessingStatus from './components/ProcessingStatus';
import Conversations from './components/Conversations';
import MonitoringDashboard from './components/MonitoringDashboard';

const App: React.FC = () => {
    const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
    const [showSidebar, setShowSidebar] = useState(true);
    const [activeView, setActiveView] = useState<'rag' | 'documents' | 'monitoring'>('rag');

    const handleConversationCreated = (conversationId: string) => {
        // When a new conversation is created from a query, switch to it
        setActiveConversationId(conversationId);
    };

    const closeSidebarOnMobile = () => {
        if (window.matchMedia('(max-width: 760px)').matches) setShowSidebar(false);
    };

    const handleConversationSelected = (conversationId: string | null) => {
        setActiveConversationId(conversationId);
        closeSidebarOnMobile();
    };

    useEffect(() => {
        if (!showSidebar || activeView !== 'rag') return;

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape' && window.matchMedia('(max-width: 760px)').matches) {
                setShowSidebar(false);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [activeView, showSidebar]);

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
                            onClick={() => setActiveView('documents')}
                            className={activeView === 'documents' ? 'active' : ''}
                        >
                            Documents
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
                            aria-label={showSidebar ? 'Hide conversations' : 'Show conversations'}
                            aria-controls="conversation-sidebar"
                            aria-expanded={showSidebar}
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
                            <>
                                <button className="sidebar-backdrop" onClick={() => setShowSidebar(false)} aria-label="Close conversations" />
                                <Conversations
                                    activeConversationId={activeConversationId}
                                    onSelectConversation={handleConversationSelected}
                                />
                            </>
                        )}
                        
                        <main className="app-content">
                            <QueryInterface 
                                activeConversationId={activeConversationId}
                                onConversationCreated={handleConversationCreated}
                            />
                            <ProcessingStatus isProcessing={false} />
                        </main>
                    </>
                ) : activeView === 'documents' ? (
                    <main className="app-content document-library-page">
                        <DocumentUpload />
                    </main>
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
