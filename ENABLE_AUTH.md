# How to Enable Authentication

## Current Status
Authentication is **DISABLED** to avoid redirect loop issues during development.

## ✅ RBAC is Fully Implemented
All authorization code is ready in the backend:
- Admin role for document upload
- User role for queries
- Viewer role for read-only access
- Tenant isolation in FAISS and Redis
- Chat history storage

## To Enable Authentication

### Option 1: Quick Toggle (Environment Variable)

Create `.env` file in backend directory:
```bash
cd /home/sachin.kumar/py/rag-system/backend
cat > .env << 'EOF'
AUTH_ENABLED=true
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=rag-system
KEYCLOAK_CLIENT_ID=rag-backend
EOF
```

Restart backend - it will pick up AUTH_ENABLED from .env file.

### Option 2: Update Config File

Edit `backend/src/core/config.py`:
```python
AUTH_ENABLED: bool = Field(
    default=True,  # Change from False to True
    description="Enable/disable authentication"
)
```

### Option 3: Use Working Auth Frontend

Replace frontend App.tsx with the working version:
```bash
cd /home/sachin.kumar/py/rag-system/frontend/src
cp App-with-auth.tsx App.tsx
```

This version:
- ✅ No redirect loops
- ✅ Simpler Keycloak initialization
- ✅ Proper token refresh
- ✅ Shows login/logout UI
- ✅ Only shows upload/query when authenticated

## Testing with Authentication

### 1. Ensure Keycloak is Running
```bash
sudo docker ps | grep keycloak
# Should show keycloak container running on port 8080
```

### 2. Verify Realm Exists
```bash
curl -s http://localhost:8080/realms/rag-system | grep -o '"realm"'
# Should output: "realm"
```

### 3. Create Test User (if not exists)
```bash
cd /home/sachin.kumar/py/rag-system
./setup-keycloak-realm.sh
```

This creates:
- User: `user@rag.local` / Password: `user123`
- Admin: `admin@rag.local` / Password: `admin123`

### 4. Enable Backend Auth
```bash
# Method 1: Environment variable
export AUTH_ENABLED=true

# Method 2: Edit config.py and change default to True
```

### 5. Use Auth-Enabled Frontend
```bash
cd frontend/src
mv App.tsx App-no-auth.tsx.bak
cp App-with-auth.tsx App.tsx
```

### 6. Restart Services
```bash
# Backend auto-reloads with uvicorn --reload
# Frontend: pkill -f vite && npm run dev
```

## Troubleshooting

### Still Getting Redirect Loops?
1. Clear browser cache completely
2. Try incognito window
3. Check browser console for errors
4. Verify redirect URIs in Keycloak:
   ```bash
   /tmp/fix-keycloak-client.sh
   ```

### "Not authenticated" errors?
- Verify AUTH_ENABLED matches between frontend expectation and backend setting
- Check backend logs for JWT validation errors
- Ensure Keycloak is accessible from backend

### Can't login?
1. Check Keycloak is running: `curl http://localhost:8080`
2. Verify realm exists: `curl http://localhost:8080/realms/rag-system`
3. Check user exists in Keycloak Admin Console: http://localhost:8080

## Recommendation

**For Production:**
1. Set AUTH_ENABLED=true via environment variable (not hardcoded)
2. Use App-with-auth.tsx (simpler, no redirect loops)
3. Configure proper Keycloak realm with real users
4. Enable JWT signature verification in auth.py
5. Use HTTPS for all Keycloak communication

**For Development:**
Keep AUTH_ENABLED=false until you're ready to test auth flows.
The system works perfectly without authentication enabled.
