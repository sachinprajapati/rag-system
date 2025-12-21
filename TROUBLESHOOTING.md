# 🔧 Fixing the "Keycloak initialization failed" Error

## The Issue

The frontend shows **"Keycloak initialization failed"** because Keycloak hasn't been started yet.

## Quick Fix: Start Keycloak

### Option 1: Using Docker Compose (Recommended)

Try these commands in order until one works:

```bash
cd /home/sachin.kumar/py/rag-system

# Try Docker Compose v2 (newer)
docker compose up keycloak -d

# If that fails, try Docker Compose v1 (older)
docker-compose up keycloak -d
```

**Wait 30-60 seconds** for Keycloak to start, then:
```bash
# Check if it's running
./check-keycloak.sh
```

### Option 2: Fix Docker Compose Issues

If you see errors like `HTTPConnection.request() got an unexpected keyword argument 'chunked'`, you have a Python package conflict.

**Fix it:**
```bash
# Upgrade urllib3
pip install --upgrade urllib3

# Or reinstall docker-compose
pip install --upgrade docker-compose
```

### Option 3: Manual Docker Command

If docker-compose doesn't work, start Keycloak manually:

```bash
docker run -d \
  --name keycloak \
  -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:23.0.0 \
  start-dev
```

## Verify Keycloak is Running

```bash
# Check container status
docker ps | grep keycloak

# Test Keycloak URL
curl http://localhost:8080

# Run diagnostic
./check-keycloak.sh
```

## After Keycloak Starts

1. **Configure Keycloak** (first time only):
   - Follow: [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md)
   - Access: http://localhost:8080
   - Login: admin / admin
   - Create realm, clients, users

2. **Reload Frontend**:
   ```bash
   # Frontend should now work
   cd frontend
   npm run dev
   # Open: http://localhost:3000
   ```

## Alternative: Disable Authentication Temporarily

If you want to test the RAG system without authentication:

1. **Update backend `.env`**:
   ```env
   AUTH_ENABLED=false
   ```

2. **Modify frontend to skip Keycloak** (temporary):
   
   Edit `frontend/src/App.tsx`:
   ```tsx
   // Comment out AuthProvider wrapper (lines 50-54)
   const App: React.FC = () => {
       return (
           // <AuthProvider>
               <AppContent />
           // </AuthProvider>
       );
   };
   ```

3. **Restart both services**

**Note:** This removes all authentication. Use only for development/testing.

## Still Having Issues?

### Check Docker Status

```bash
# Is Docker running?
systemctl status docker

# Start Docker if needed
sudo systemctl start docker
```

### View Logs

```bash
# Docker logs
docker logs keycloak

# Or with docker-compose
docker-compose logs keycloak

# Follow logs in real-time
docker logs -f keycloak
```

### Common Errors

**"Cannot connect to Docker daemon"**
```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
# Logout and login again
```

**"Port 8080 already in use"**
```bash
# Find what's using port 8080
lsof -i :8080

# Kill it or change Keycloak port in docker-compose.yml
```

**"Keycloak takes too long to start"**
- Wait 60-90 seconds on first start
- Check CPU/memory: `docker stats`
- View startup progress: `docker logs -f keycloak`

## Updated Frontend Error Page

Your frontend now shows a helpful error page with:
- ✅ Step-by-step setup instructions
- ✅ Link to Keycloak (http://localhost:8080)
- ✅ Link to KEYCLOAK_SETUP.md
- ✅ Full error details

## Success Indicators

✅ `./check-keycloak.sh` passes all checks  
✅ http://localhost:8080 loads in browser  
✅ Frontend shows login button instead of error  
✅ No errors in browser console (F12)

---

**Next Step:** Start Keycloak with one of the commands above, then reload your frontend!
