/**
 * Keycloak Authentication Context
 * Manages authentication state and token handling
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import Keycloak from 'keycloak-js';
import { keycloakConfig, keycloakInitOptions } from '../config/keycloak';

interface AuthContextType {
  keycloak: Keycloak | null;
  authenticated: boolean;
  user: UserInfo | null;
  login: () => void;
  logout: () => void;
  getToken: () => Promise<string | undefined>;
  hasRole: (role: string) => boolean;
  loading: boolean;
  error: string | null;
}

interface UserInfo {
  userId: string;
  username: string;
  email: string;
  tenantId: string;
  roles: string[];
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [keycloak, setKeycloak] = useState<Keycloak | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    let initTimeout: ReturnType<typeof setTimeout>;

    const initKeycloak = async () => {
      try {
        if (!mounted) return;
        
        console.log('Starting Keycloak initialization...');
        const keycloakInstance = new Keycloak(keycloakConfig);
        
        // Set a shorter timeout
        initTimeout = setTimeout(() => {
          if (mounted && loading) {
            console.error('Keycloak initialization timeout - treating as not authenticated');
            setKeycloak(keycloakInstance);
            setAuthenticated(false);
            setLoading(false);
            setError(null); // Clear error, allow to proceed
          }
        }, 5000); // 5 second timeout
        
        console.log('Calling keycloak.init()...');
        const authenticated = await keycloakInstance.init(keycloakInitOptions);
        
        clearTimeout(initTimeout);
        
        if (!mounted) return;
        
        console.log('Keycloak initialized. Authenticated:', authenticated);

        setKeycloak(keycloakInstance);
        setAuthenticated(authenticated);

        if (authenticated) {
          console.log('User is authenticated, loading user info...');
          await loadUserInfo(keycloakInstance);
        } else {
          console.log('User is not authenticated. Login available via UI.');
        }

        // Token refresh
        keycloakInstance.onTokenExpired = () => {
          console.log('Token expired, refreshing...');
          keycloakInstance
            .updateToken(30)
            .then((refreshed) => {
              if (refreshed && mounted) {
                console.log('Token refreshed successfully');
              }
            })
            .catch(() => {
              console.error('Failed to refresh token');
              if (authenticated) {
                keycloakInstance.logout();
              }
            });
        };

        if (mounted) {
          setLoading(false);
          setError(null);
          console.log('Keycloak initialization complete!');
        }
      } catch (err: any) {
        clearTimeout(initTimeout);
        if (!mounted) return;
        
        console.error('Keycloak initialization error:', err);
        // Don't block the UI - proceed without auth
        setAuthenticated(false);
        setLoading(false);
        setError(null); // Don't show error, just proceed
      }
    };

    initKeycloak();

    return () => {
      mounted = false;
      if (initTimeout) clearTimeout(initTimeout);
    };
  }, []);

  const loadUserInfo = async (kc: Keycloak) => {
    try {
      const profile = await kc.loadUserProfile();
      const token = kc.tokenParsed;

      const userInfo: UserInfo = {
        userId: token?.sub || '',
        username: token?.preferred_username || profile.username || '',
        email: profile.email || '',
        tenantId: token?.tenant_id || 'default',
        roles: extractRoles(token),
      };

      setUser(userInfo);
    } catch (error) {
      console.error('Failed to load user info:', error);
    }
  };

  const extractRoles = (token: any): string[] => {
    if (!token) return [];

    const roles: string[] = [];

    // Realm roles
    if (token.realm_access?.roles) {
      roles.push(...token.realm_access.roles);
    }

    // Client roles
    if (token.resource_access) {
      Object.values(token.resource_access).forEach((access: any) => {
        if (access.roles) {
          roles.push(...access.roles);
        }
      });
    }

    return roles;
  };

  const login = () => {
    keycloak?.login();
  };

  const logout = () => {
    keycloak?.logout();
  };

  const getToken = async (): Promise<string | undefined> => {
    if (!keycloak) return undefined;

    try {
      await keycloak.updateToken(30);
      return keycloak.token;
    } catch (error) {
      console.error('Failed to get token:', error);
      return undefined;
    }
  };

  const hasRole = (role: string): boolean => {
    return user?.roles.includes(role) || false;
  };

  return (
    <AuthContext.Provider
      value={{
        keycloak,
        authenticated,
        user,
        login,
        logout,
        getToken,
        hasRole,
        loading,
        error,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
