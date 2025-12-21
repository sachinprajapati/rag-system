# RBAC Authorization Implementation

## Overview
This RAG system implements Role-Based Access Control (RBAC) using Keycloak OAuth2/OpenID Connect with tenant-level isolation.

## Roles

### 1. Admin Role
**Capabilities:**
- Upload and manage documents
- Manage users (via Keycloak)
- Access all user/viewer capabilities

**API Endpoints:**
- `POST /api/documents/upload` - Upload PDF documents
- All USER and VIEWER endpoints

### 2. User Role
**Capabilities:**
- Ask questions and query the RAG system
- View chat history
- Clear own chat history
- List documents in tenant

**API Endpoints:**
- `POST /api/query` - Query the RAG system
- `GET /api/query/history` - Get chat history
- `DELETE /api/query/history` - Clear chat history
- `GET /api/documents/list` - List documents

### 3. Viewer Role
**Capabilities:**
- Read-only access
- View documents list only

**API Endpoints:**
- `GET /api/documents/list` - List documents (read-only)

## Tenant Isolation

### Document Storage
- Each document chunk stored with `tenant_id` in FAISS metadata
- Upload requires `tenant_id` from authenticated user
- Metadata includes:
  ```python
  {
      "file_path": str,
      "file_name": str,
      "chunk_index": int,
      "text": str,
      "tenant_id": str,      # Tenant isolation
      "uploaded_by": str     # User who uploaded
  }
  ```

### Vector Search
- FAISS search filtered by `tenant_id`
- Users only see documents from their tenant
- Implementation: Search with 10x results, then filter by tenant

### Chat History
- Stored in Redis with key pattern: `chat:history:{tenant_id}:{user_id}`
- Scoped by both `user_id` and `tenant_id`
- Automatic storage on every query (when authenticated)
- 30-day expiration, 100 message limit per user

## Authentication Flow

### 1. Token Validation
```python
# JWT token from Keycloak
Authorization: Bearer <token>

# Token contains:
{
    "sub": "user_id",
    "preferred_username": "username",
    "email": "user@example.com",
    "tenant_id": "tenant_123",  # Custom claim
    "realm_access": {
        "roles": ["admin", "user"]
    }
}
```

### 2. Role Extraction
Roles extracted from:
- `realm_access.roles` - Keycloak realm roles
- `resource_access.{client}.roles` - Client-specific roles

### 3. Dependency Injection
```python
# Require admin role
@router.post("/upload")
async def upload(user: TokenData = Depends(require_admin)):
    ...

# Require user or admin
@router.post("/query")
async def query(user: TokenData = Depends(require_user)):
    ...

# Require any authenticated role
@router.get("/list")
async def list_docs(user: TokenData = Depends(require_viewer)):
    ...
```

## API Endpoints Summary

| Endpoint | Method | Required Role | Tenant Isolated |
|----------|--------|---------------|-----------------|
| `/api/documents/upload` | POST | admin | Yes |
| `/api/documents/list` | GET | viewer | Yes |
| `/api/query` | POST | user | Yes |
| `/api/query/history` | GET | user | Yes |
| `/api/query/history` | DELETE | user | Yes |
| `/api/health` | GET | none | No |

## Configuration

### Enable/Disable Authentication
```python
# backend/src/core/config.py
AUTH_ENABLED = True  # Set to False for development without Keycloak
```

### Keycloak Settings
```python
KEYCLOAK_URL = "http://localhost:8080"
KEYCLOAK_REALM = "rag-system"
KEYCLOAK_CLIENT_ID = "rag-frontend"
```

## Security Considerations

### Production Checklist
- [ ] Enable JWT signature verification (`verify_signature=True`)
- [ ] Verify token audience (`verify_aud=True`)
- [ ] Use HTTPS for all Keycloak communication
- [ ] Rotate Keycloak client secrets regularly
- [ ] Implement rate limiting on API endpoints
- [ ] Add audit logging for admin actions
- [ ] Enable CORS only for trusted origins
- [ ] Use secure Redis password

### Current Development Settings
⚠️ **WARNING**: JWT signature verification is disabled for development
```python
# In production, set:
options = {
    "verify_signature": True,   # ✅ Enable in production
    "verify_aud": True,          # ✅ Verify audience
    "verify_exp": True,          # ✅ Already enabled
}
```

## Testing

### Without Authentication
```bash
# Set AUTH_ENABLED=False in config.py
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

### With Authentication
```bash
# Get token from Keycloak
TOKEN=$(curl -X POST http://localhost:8080/realms/rag-system/protocol/openid-connect/token \
  -d "client_id=rag-frontend" \
  -d "username=user@rag.local" \
  -d "password=user123" \
  -d "grant_type=password" | jq -r '.access_token')

# Use token in request
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

## Role Assignment in Keycloak

### Via Keycloak Admin UI
1. Login to Keycloak Admin Console: http://localhost:8080
2. Select realm: `rag-system`
3. Users → Select user → Role Mapping
4. Assign realm roles: `admin`, `user`, or `viewer`

### Via API Script
```bash
# See setup-keycloak-realm.sh for automated role assignment
./setup-keycloak-realm.sh
```

## Multi-Tenancy Implementation

### How It Works
1. **Token contains tenant_id**: Custom JWT claim added during user creation
2. **Document upload**: Stores `tenant_id` with each vector embedding
3. **Query search**: Filters results to match user's `tenant_id`
4. **Chat history**: Redis keys include `tenant_id` for isolation
5. **Document listing**: Only shows documents from user's tenant

### Adding tenant_id to Users
```python
# In Keycloak, add custom attribute to user:
{
    "attributes": {
        "tenant_id": ["company_abc"]
    }
}

# Configure client mapper to include in JWT
# Mapper type: User Attribute
# Attribute: tenant_id
# Token Claim Name: tenant_id
```

## Architecture Diagram

```
┌─────────────┐
│  Frontend   │ (Keycloak.js auth)
└──────┬──────┘
       │ JWT Token
       ▼
┌─────────────────────────────┐
│  FastAPI Backend            │
│  ┌─────────────────────┐   │
│  │ JWT Validator       │   │
│  │ - Verify signature  │   │
│  │ - Extract claims    │   │
│  │ - Check roles       │   │
│  └──────────┬──────────┘   │
│             │               │
│  ┌──────────▼──────────┐   │
│  │ RBAC Dependencies   │   │
│  │ - require_admin     │   │
│  │ - require_user      │   │
│  │ - require_viewer    │   │
│  └──────────┬──────────┘   │
│             │               │
│  ┌──────────▼──────────┐   │
│  │ Tenant Filtering    │   │
│  │ FAISS search        │   │
│  │ Redis chat history  │   │
│  └─────────────────────┘   │
└─────────────────────────────┘
```

## Troubleshooting

### 403 Forbidden
- Check user has required role in Keycloak
- Verify JWT token contains roles in `realm_access.roles`
- Ensure AUTH_ENABLED matches frontend auth state

### Tenant Isolation Not Working
- Verify `tenant_id` is in JWT token (custom claim)
- Check FAISS metadata includes `tenant_id` for all documents
- Re-upload documents if migrating from non-tenant system

### Chat History Not Storing
- Verify Redis is running: `redis-cli ping`
- Check Redis connection settings in config.py
- Ensure user is authenticated (chat history requires auth)
