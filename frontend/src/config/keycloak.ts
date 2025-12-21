/**
 * Keycloak configuration
 */
export const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'rag-system',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'rag-frontend',
};

export const keycloakInitOptions = {
  onLoad: 'check-sso' as const,
  checkLoginIframe: false,
  pkceMethod: 'S256' as const,
  enableLogging: true,
};
