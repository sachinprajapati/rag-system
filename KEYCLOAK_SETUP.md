# Keycloak Authentication Setup Guide

## Overview
This guide will help you configure Keycloak for the RAG System with OAuth2/OpenID Connect authentication.

## Prerequisites
- Docker and Docker Compose installed
- Backend running on http://localhost:8000
- Frontend running on http://localhost:3000

## Step 1: Start Keycloak Server

```bash
cd /home/sachin.kumar/py/rag-system
docker-compose up keycloak -d
```

Wait for Keycloak to start (about 30-60 seconds). Check status:
```bash
docker-compose logs -f keycloak
```

Look for: `Keycloak 23.0.0 started`

## Step 2: Access Keycloak Admin Console

1. Open browser: http://localhost:8080
2. Click "Administration Console"
3. Login with:
   - **Username**: `admin`
   - **Password**: `admin`

## Step 3: Create Realm

1. Click dropdown at top left (currently showing "master")
2. Click "Create Realm"
3. Enter:
   - **Realm name**: `rag-system`
4. Click "Create"

## Step 4: Create Backend Client

1. In left sidebar, click "Clients"
2. Click "Create client"
3. **General Settings**:
   - **Client type**: OpenID Connect
   - **Client ID**: `rag-backend`
   - Click "Next"

4. **Capability config**:
   - ✅ Client authentication: ON
   - ✅ Authorization: OFF
   - ✅ Authentication flow: Check "Service accounts roles"
   - Click "Next"

5. **Login settings**:
   - Leave defaults
   - Click "Save"

6. **Get Client Secret**:
   - Go to "Credentials" tab
   - Copy the "Client secret" value
   - Update your `.env` file:
     ```env
     KEYCLOAK_CLIENT_SECRET=<paste-secret-here>
     ```

## Step 5: Create Frontend Client

1. Click "Clients" → "Create client"
2. **General Settings**:
   - **Client type**: OpenID Connect
   - **Client ID**: `rag-frontend`
   - Click "Next"

3. **Capability config**:
   - ❌ Client authentication: OFF (public client)
   - ✅ Authorization: OFF
   - ✅ Authentication flow: Check "Standard flow" and "Direct access grants"
   - Click "Next"

4. **Login settings**:
   - **Valid redirect URIs**: 
     - `http://localhost:3000/*`
     - `http://localhost:3000`
   - **Valid post logout redirect URIs**:
     - `http://localhost:3000/*`
     - `http://localhost:3000`
   - **Web origins**: `http://localhost:3000`
   - Click "Save"

## Step 6: Create Roles

1. In left sidebar, click "Realm roles"
2. Click "Create role"

**Create Admin Role:**
- **Role name**: `admin`
- **Description**: Administrator with full access
- Click "Save"

**Create User Role:**
- Click "Create role" again
- **Role name**: `user`
- **Description**: Regular user access
- Click "Save"

## Step 7: Create Test Users

### Create Admin User

1. In left sidebar, click "Users"
2. Click "Add user"
3. **User details**:
   - **Username**: `admin@rag.local`
   - **Email**: `admin@rag.local`
   - **First name**: `Admin`
   - **Last name**: `User`
   - ✅ Email verified: ON
   - Click "Create"

4. **Set Password**:
   - Go to "Credentials" tab
   - Click "Set password"
   - **Password**: `admin123` (or your choice)
   - ❌ Temporary: OFF
   - Click "Save"
   - Confirm "Set password"

5. **Assign Roles**:
   - Go to "Role mapping" tab
   - Click "Assign role"
   - Select: `admin` and `user`
   - Click "Assign"

### Create Regular User

1. Click "Users" → "Add user"
2. **User details**:
   - **Username**: `user@rag.local`
   - **Email**: `user@rag.local`
   - **First name**: `Test`
   - **Last name**: `User`
   - ✅ Email verified: ON
   - Click "Create"

3. **Set Password**:
   - Go to "Credentials" tab
   - Click "Set password"
   - **Password**: `user123` (or your choice)
   - ❌ Temporary: OFF
   - Click "Save"

4. **Assign Roles**:
   - Go to "Role mapping" tab
   - Click "Assign role"
   - Select: `user`
   - Click "Assign"

## Step 8: Configure Client Scopes (Optional)

To include roles in JWT tokens:

1. Go to "Client scopes" → "roles" → "Mappers"
2. Edit "realm roles" mapper:
   - ✅ Add to ID token: ON
   - ✅ Add to access token: ON
   - ✅ Add to userinfo: ON
3. Click "Save"

## Step 9: Verify Configuration

### Check Realm Settings
1. Go to "Realm settings"
2. "General" tab:
   - Ensure "Enabled" is ON
3. "Login" tab:
   - ✅ User registration: OFF (for production)
   - ✅ Forgot password: ON
   - ✅ Remember me: ON

### Get OpenID Configuration
```bash
curl http://localhost:8080/realms/rag-system/.well-known/openid-configuration | jq
```

Expected endpoints:
- `authorization_endpoint`: http://localhost:8080/realms/rag-system/protocol/openid-connect/auth
- `token_endpoint`: http://localhost:8080/realms/rag-system/protocol/openid-connect/token
- `userinfo_endpoint`: http://localhost:8080/realms/rag-system/protocol/openid-connect/userinfo

## Step 10: Update Environment Variables

Edit `/home/sachin.kumar/py/rag-system/.env`:

```env
# Authentication
AUTH_ENABLED=true
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=rag-system
KEYCLOAK_CLIENT_ID=rag-backend
KEYCLOAK_CLIENT_SECRET=<your-client-secret-from-step-4>
KEYCLOAK_FRONTEND_CLIENT_ID=rag-frontend
```

## Step 11: Restart Backend

```bash
# Stop backend if running (Ctrl+C)
cd /home/sachin.kumar/py/rag-system/backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Step 12: Test Authentication Flow

### Test Frontend Login

1. Open http://localhost:3000
2. Click "Login" button
3. You'll be redirected to Keycloak login page
4. Login with:
   - **Username**: `user@rag.local`
   - **Password**: `user123`
5. You should be redirected back to RAG System
6. User profile should show your name and roles

### Test Admin Access

1. Logout (if logged in)
2. Login as admin:
   - **Username**: `admin@rag.local`
   - **Password**: `admin123`
3. Test admin-only endpoint:
   ```bash
   # Get token first
   TOKEN=$(curl -X POST http://localhost:8080/realms/rag-system/protocol/openid-connect/token \
     -d "client_id=rag-frontend" \
     -d "username=admin@rag.local" \
     -d "password=admin123" \
     -d "grant_type=password" | jq -r .access_token)
   
   # Call admin endpoint
   curl http://localhost:8000/api/auth/admin-only \
     -H "Authorization: Bearer $TOKEN"
   ```

### Test Protected API Endpoints

**Upload Document (requires authentication):**
```bash
TOKEN=$(curl -X POST http://localhost:8080/realms/rag-system/protocol/openid-connect/token \
  -d "client_id=rag-frontend" \
  -d "username=user@rag.local" \
  -d "password=user123" \
  -d "grant_type=password" | jq -r .access_token)

curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"
```

**Query (requires authentication):**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?"}'
```

## Troubleshooting

### Issue: "Failed to initialize Keycloak"
- Check Keycloak is running: `docker-compose ps`
- Verify URL in `.env` matches: `KEYCLOAK_URL=http://localhost:8080`
- Check browser console for CORS errors

### Issue: "Invalid token" or "401 Unauthorized"
- Verify realm name matches: `rag-system`
- Check client IDs are correct
- Ensure user has proper roles assigned
- Check token hasn't expired (default: 5 minutes)

### Issue: Redirect URI mismatch
- In Keycloak admin, check client's "Valid redirect URIs"
- Must include: `http://localhost:3000/*`
- Must include: `http://localhost:3000`

### Issue: CORS errors
- Backend CORS should allow http://localhost:8080 (Keycloak)
- Check `/backend/src/main.py` CORS configuration

### Debug: View JWT Token Contents
```bash
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq
```

Look for:
- `sub`: User ID
- `email`: User email
- `preferred_username`: Username
- `realm_access.roles`: User roles

## Production Considerations

### Security Hardening

1. **Change Default Credentials**:
   - Change Keycloak admin password
   - Use strong passwords for all users

2. **Enable HTTPS**:
   - Configure SSL/TLS certificates
   - Update URLs to https://

3. **Token Validation**:
   - Enable signature verification in `/backend/src/core/auth.py`
   - Set `verify=True` in JWT validation

4. **Environment Variables**:
   - Never commit `.env` to git
   - Use secrets management (AWS Secrets Manager, HashiCorp Vault)

5. **Rate Limiting**:
   - Add rate limiting to authentication endpoints
   - Implement account lockout after failed attempts

6. **Session Management**:
   - Configure token expiration times
   - Implement token refresh mechanism
   - Add session timeout

### Multi-Tenant Setup

For multi-tenant RAG system:

1. **Custom Claim for Tenant ID**:
   - Go to "Client scopes" → Create scope "tenant-id"
   - Add mapper: "User Attribute" → Map "tenant_id" attribute
   - Add scope to `rag-frontend` client

2. **Backend Changes**:
   - Extract `tenant_id` from JWT in `get_current_user()`
   - Filter documents/queries by tenant_id
   - Implement tenant isolation in FAISS indexes

## Additional Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OAuth 2.0 RFC](https://datatracker.ietf.org/doc/html/rfc6749)
- [OpenID Connect Spec](https://openid.net/specs/openid-connect-core-1_0.html)
- [keycloak-js Documentation](https://www.keycloak.org/docs/latest/securing_apps/#_javascript_adapter)

## Quick Reference

### Default Credentials
- **Keycloak Admin**: admin / admin
- **Test Admin**: admin@rag.local / admin123
- **Test User**: user@rag.local / user123

### URLs
- **Keycloak Admin**: http://localhost:8080
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### Clients
- **Backend**: rag-backend (confidential)
- **Frontend**: rag-frontend (public)

### Roles
- **admin**: Full system access
- **user**: Basic user access
