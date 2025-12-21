/**
 * User Profile and Authentication UI Component
 */
import React from 'react';
import { useAuth } from '../context/AuthContext';

const UserProfile: React.FC = () => {
  const { authenticated, user, login, logout, loading } = useAuth();

  if (loading) {
    return <div className="user-profile loading">Loading...</div>;
  }

  if (!authenticated) {
    return (
      <div className="user-profile">
        <button onClick={login} className="btn-login">
          Login with Keycloak
        </button>
      </div>
    );
  }

  return (
    <div className="user-profile authenticated">
      <div className="user-info">
        <div className="user-avatar">
          {user?.username?.charAt(0).toUpperCase() || 'U'}
        </div>
        <div className="user-details">
          <div className="username">{user?.username || 'User'}</div>
          {user?.email && <div className="email">{user.email}</div>}
          {user?.tenantId && <div className="tenant">Tenant: {user.tenantId}</div>}
          {user?.roles && user.roles.length > 0 && (
            <div className="roles">
              Roles: {user.roles.filter(r => !r.startsWith('default-')).join(', ') || 'user'}
            </div>
          )}
        </div>
      </div>
      <button onClick={logout} className="btn-logout">
        Logout
      </button>
    </div>
  );
};

export default UserProfile;
