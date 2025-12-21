# Authorization & Access Control - Implementation Complete

## Summary
Successfully implemented comprehensive RBAC (Role-Based Access Control) and multi-tenant isolation for the RAG system using Keycloak OAuth2/OpenID Connect.

## ✅ Completed Features

### 1. Role-Based Access Control (RBAC)
Three roles implemented with distinct permissions:

**Admin Role** (`require_admin`)
- Upload documents: `POST /api/documents/upload`
- Manage all system resources
- Full access to user and viewer capabilities

**User Role** (`require_user`)  
- Query RAG system: `POST /api/query`
- Access chat history: `GET /api/query/history`
- Clear chat history: `DELETE /api/query/history`
- List documents: `GET /api/documents/list`

**Viewer Role** (`require_viewer`)
- List documents: `GET /api/documents/list` (read-only)

### 2. Tenant-Level Isolation

**FAISS Vector Database**
- Each document chunk includes `tenant_id` in metadata
- Search filtered by user's tenant: `search_faiss(..., tenant_id=user.tenant_id)`
- Users only retrieve documents from their own tenant
- Implementation: Search with 10x results, filter by tenant, return top-k

**Document Metadata Structure**
```python
{
    "file_path": str,
    "file_name": str,
    "chunk_index": int,
    "text": str,
    "tenant_id": str,      # ← Tenant isolation
    "uploaded_by": str     # ← User tracking
}
```

**Chat History**
- Redis key pattern: `chat:history:{tenant_id}:{user_id}`
- Double-scoped: both user AND tenant
- Automatic storage on every authenticated query
- 30-day TTL, 100 message limit per user

### 3. Authentication Dependencies

**Core Auth Module** (`src/core/auth.py`)
- `get_current_user()` - Extracts and validates JWT token
- `require_admin()` - Admin role required
- `require_user()` - User or admin role required  
- `require_viewer()` - Any role (viewer/user/admin) required
- `get_optional_user()` - Optional auth for mixed endpoints

**Token Data Extraction**
```python
class TokenData:
    user_id: str          # from JWT 'sub'
    username: str         # from 'preferred_username'
    email: str            # from 'email'
    tenant_id: str        # from custom claim 'tenant_id'
    roles: List[str]      # from 'realm_access.roles'
```

### 4. API Endpoint Protection

| Endpoint | Method | Role Required | Tenant Filtered |
|----------|--------|---------------|-----------------|
| `/api/documents/upload` | POST | **admin** | ✅ Yes |
| `/api/documents/list` | GET | viewer | ✅ Yes |
| `/api/query` | POST | **user** | ✅ Yes |
| `/api/query/history` | GET | user | ✅ Yes |
| `/api/query/history` | DELETE | user | ✅ Yes |
| `/api/health` | GET | none | No |

### 5. Files Modified/Created

**Modified Files:**
- ✅ `backend/src/core/auth.py` - Added role dependencies
- ✅ `backend/src/db/faiss_manager.py` - Added tenant filtering
- ✅ `backend/src/services/document_ingestion.py` - Store tenant_id
- ✅ `backend/src/services/retrieval.py` - Filter by tenant_id
- ✅ `backend/src/services/generation.py` - Pass tenant_id
- ✅ `backend/src/api/routes/documents.py` - Admin-only upload, viewer list
- ✅ `backend/src/api/routes/query.py` - User role, chat history

**Created Files:**
- ✅ `backend/src/models/chat.py` - Chat history models
- ✅ `backend/src/services/chat_history.py` - Redis-based chat storage
- ✅ `RBAC_IMPLEMENTATION.md` - Comprehensive documentation
- ✅ `AUTH_SUMMARY.md` - This file

## 🔒 Security Implementation

### What's Protected
1. **Document Upload** - Admin only, prevents unauthorized data injection
2. **Query Results** - Tenant-filtered, no cross-tenant data leakage
3. **Chat History** - User+tenant scoped, privacy preserved
4. **Document List** - Tenant-filtered, no information disclosure

### Current State
- ✅ Role extraction from JWT working
- ✅ Tenant isolation implemented
- ✅ Chat history storage functional
- ⚠️ JWT signature verification **disabled** (development mode)
- ⚠️ AUTH_ENABLED currently **False** (for testing)

## 🚀 Activation Instructions

### Step 1: Enable Authentication
```bash
# Edit backend/src/core/config.py
AUTH_ENABLED: bool = True  # Change from False to True
```

### Step 2: Configure Keycloak Users with Roles
```bash
# Run Keycloak realm setup (already done previously)
cd /home/sachin.kumar/py/rag-system
./setup-keycloak-realm.sh
```

### Step 3: Add tenant_id to Keycloak Users
In Keycloak Admin Console:
1. Go to Users → Select user
2. Attributes tab
3. Add attribute: `tenant_id` = `company_abc`
4. Save

Configure Client Mapper:
1. Clients → `rag-frontend` → Mappers
2. Create new mapper:
   - Name: `tenant-id-mapper`
   - Mapper Type: `User Attribute`
   - User Attribute: `tenant_id`
   - Token Claim Name: `tenant_id`
   - Claim JSON Type: `String`

### Step 4: Restart Backend
```bash
# The uvicorn server will auto-reload with --reload flag
# Changes to config.py will be picked up automatically
```

### Step 5: Update Frontend
Frontend already has Keycloak integration configured:
- `frontend/src/config/keycloak.ts` - Keycloak client config
- `frontend/.env` - Environment variables

To re-enable auth in frontend, restore the AuthProvider in App.tsx (currently simplified for development).

## 🧪 Testing

### Test Without Auth (Current State)
```bash
# AUTH_ENABLED=False
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

### Test With Auth (After Enabling)
```bash
# Get token from Keycloak
TOKEN=$(curl -X POST http://localhost:8080/realms/rag-system/protocol/openid-connect/token \
  -d "client_id=rag-frontend" \
  -d "username=user@rag.local" \
  -d "password=user123" \
  -d "grant_type=password" | jq -r '.access_token')

# Test admin endpoint (will fail without admin role)
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"

# Test user endpoint
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'

# Test chat history
curl -X GET http://localhost:8000/api/query/history \
  -H "Authorization: Bearer $TOKEN"
```

## 📊 Data Flow

### Upload Flow (Admin Only)
```
User (admin role) → JWT Token → Backend
                                   ↓
                          require_admin() check
                                   ↓
                          Extract tenant_id from token
                                   ↓
                          Parse PDF → Embed → Store in FAISS
                                   ↓
                          Metadata includes tenant_id
```

### Query Flow (User Role)
```
User (user/admin role) → JWT Token → Backend
                                        ↓
                               require_user() check
                                        ↓
                               Extract tenant_id from token
                                        ↓
                               Query embedding → FAISS search
                                        ↓
                               Filter results by tenant_id
                                        ↓
                               Store in chat history (Redis)
                                        ↓
                               Return filtered results
```

## ⚠️ Important Notes

### Production Checklist
Before deploying to production:
- [ ] Enable JWT signature verification in `auth.py`
- [ ] Set `AUTH_ENABLED=True`
- [ ] Use HTTPS for Keycloak and backend
- [ ] Rotate Keycloak client secrets
- [ ] Enable Redis password authentication
- [ ] Configure proper CORS origins
- [ ] Add rate limiting
- [ ] Implement audit logging

### Current Limitations
1. **No persistent document database** - Documents only in FAISS/Redis
2. **Simple role hierarchy** - No nested or custom role logic
3. **No user management API** - Must use Keycloak Admin UI
4. **Basic tenant assignment** - Manual configuration in Keycloak

### Future Enhancements
- [ ] PostgreSQL for document metadata persistence
- [ ] Admin API for user/tenant management
- [ ] Hierarchical tenants (parent/child organizations)
- [ ] Document deletion endpoint
- [ ] Bulk document upload
- [ ] Advanced analytics per tenant
- [ ] Export chat history

## 📝 Quick Reference

### Environment Variables
```bash
# Backend (.env or config.py)
AUTH_ENABLED=True
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=rag-system
KEYCLOAK_CLIENT_ID=rag-frontend
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Common Commands
```bash
# Check Keycloak status
./check-keycloak.sh

# Setup realm and users
./setup-keycloak-realm.sh

# Start backend
cd backend && source .venv/bin/activate
uvicorn src.main:app --reload

# Start frontend
cd frontend && npm run dev

# Check Redis
redis-cli ping
```

## 🎉 Conclusion

The RAG system now has enterprise-grade authorization and multi-tenancy:
- ✅ RBAC with 3 roles (admin, user, viewer)
- ✅ Tenant-level data isolation (FAISS + Redis)
- ✅ Automatic chat history tracking
- ✅ Production-ready architecture (with noted security enhancements needed)

**Authentication is currently DISABLED for development.**  
Set `AUTH_ENABLED=True` when ready to activate full security.
