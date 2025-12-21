import React from 'react';
import DocumentUpload from './components/DocumentUpload';
import QueryInterface from './components/QueryInterface';
import ProcessingStatus from './components/ProcessingStatus';

const App: React.FC = () => {
    return (
        <div className="App">
            <header className="app-header">
                <div>
                    <h1>RAG System</h1>
                    <p style={{ color: '#fff', margin: 0 }}>Production-Grade RAG System with RBAC</p>
                </div>
                <div style={{ color: 'white', fontSize: '0.9rem' }}>
                    🔓 Auth: Disabled | RBAC Ready
                </div>
            </header>
            
            <main className="app-content">
                <DocumentUpload />
                <QueryInterface />
                <ProcessingStatus isProcessing={false} />
            </main>
        </div>
    );
};

export default App;
