import React, { useState, useEffect } from 'react';
import Keycloak from 'keycloak-js';
import DocumentUpload from './components/DocumentUpload';
import QueryInterface from './components/QueryInterface';
import ProcessingStatus from './components/ProcessingStatus';
import { setTokenGetter } from './services/api';

const keycloak = new Keycloak({
  url: 'http://localhost:8080',
  realm: 'rag-system',
  clientId: 'rag-frontend',
});

const App: React.FC = () => {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState('');
  const [roles, setRoles] = useState<string[]>([]);

  useEffect(() => {
    keycloak.init({
      onLoad: 'check-sso',
      checkLoginIframe: false,
      pkceMethod: 'S256',
    }).then((auth) => {
      setAuthenticated(auth);
      setLoading(false);

      if (auth && keycloak.tokenParsed) {
        setUsername(keycloak.tokenParsed.preferred_username || 'User');
        const userRoles = keycloak.tokenParsed.realm_access?.roles || [];
        setRoles(userRoles.filter(r => !r.startsWith('default-')));

        // Set token getter for API calls
        setTokenGetter(async () => {
          await keycloak.updateToken(30);
          return keycloak.token;
        });
      }

      // Token refresh
      setInterval(() => {
        keycloak.updateToken(30).catch(() => {
          console.error('Failed to refresh token');
        });
      }, 30000);
    }).catch(() => {
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="App">
        <header className="app-header">
          <h1>RAG System</h1>
        </header>
        <main className="app-content">
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p>Loading...</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="app-header">
        <div>
          <h1>RAG System</h1>
          <p style={{ color: '#fff', margin: 0 }}>Production-Grade RAG System with RBAC</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          {authenticated ? (
            <>
              <div style={{ color: 'white', textAlign: 'right' }}>
                <div style={{ fontWeight: 'bold' }}>{username}</div>
                {roles.length > 0 && (
                  <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>
                    {roles.join(', ')}
                  </div>
                )}
              </div>
              <button 
                onClick={() => keycloak.logout()}
                style={{
                  backgroundColor: '#e74c3c',
                  color: 'white',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '5px',
                  cursor: 'pointer',
                }}
              >
                Logout
              </button>
            </>
          ) : (
            <button 
              onClick={() => keycloak.login()}
              style={{
                backgroundColor: '#3498db',
                color: 'white',
                border: 'none',
                padding: '10px 20px',
                borderRadius: '5px',
                cursor: 'pointer',
              }}
            >
              Login with Keycloak
            </button>
          )}
        </div>
      </header>
      
      <main className="app-content">
        {authenticated ? (
          <>
            <DocumentUpload />
            <QueryInterface />
            <ProcessingStatus isProcessing={false} />
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '60px 20px' }}>
            <h2>Welcome to RAG System</h2>
            <p style={{ fontSize: '1.2rem', color: '#666' }}>
              Please login to upload documents and query the system
            </p>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
