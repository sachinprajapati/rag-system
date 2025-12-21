#!/bin/bash

set -e

echo "=========================================="
echo "Keycloak Complete Setup for RAG System"
echo "=========================================="
echo ""

# Get admin token
echo "1. Getting admin access token..."
RESPONSE=$(curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" \
  -d "client_id=admin-cli")

TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Failed to get admin token. Is Keycloak running?"
  exit 1
fi

echo "   ✓ Token obtained"

# Create frontend client
echo "2. Creating frontend client 'rag-frontend'..."
curl -s -X POST http://localhost:8080/admin/realms/rag-system/clients \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "rag-frontend",
    "enabled": true,
    "publicClient": true,
    "redirectUris": ["http://localhost:3000/*"],
    "webOrigins": ["http://localhost:3000"],
    "standardFlowEnabled": true,
    "directAccessGrantsEnabled": true
  }' > /dev/null 2>&1
echo "   ✓ Frontend client created"

# Create roles
echo "3. Creating roles..."
curl -s -X POST http://localhost:8080/admin/realms/rag-system/roles \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "user", "description": "Regular user"}' > /dev/null 2>&1

curl -s -X POST http://localhost:8080/admin/realms/rag-system/roles \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "admin", "description": "Administrator"}' > /dev/null 2>&1
echo "   ✓ Roles created"

# Create test user
echo "4. Creating test user 'user@rag.local'..."
curl -s -X POST http://localhost:8080/admin/realms/rag-system/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@rag.local",
    "email": "user@rag.local",
    "firstName": "Test",
    "lastName": "User",
    "enabled": true,
    "emailVerified": true
  }' > /dev/null 2>&1

# Get user ID
USER_ID=$(curl -s http://localhost:8080/admin/realms/rag-system/users?username=user@rag.local \
  -H "Authorization: Bearer $TOKEN" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

# Set password
curl -s -X PUT http://localhost:8080/admin/realms/rag-system/users/$USER_ID/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "password", "value": "user123", "temporary": false}' > /dev/null 2>&1

# Get role ID and assign
ROLE_ID=$(curl -s http://localhost:8080/admin/realms/rag-system/roles/user \
  -H "Authorization: Bearer $TOKEN" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

curl -s -X POST http://localhost:8080/admin/realms/rag-system/users/$USER_ID/role-mappings/realm \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "[{\"id\": \"$ROLE_ID\", \"name\": \"user\"}]" > /dev/null 2>&1
echo "   ✓ User created: user@rag.local / user123"

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Test Login:"
echo "  Username: user@rag.local"
echo "  Password: user123"
echo ""
echo "Now:"
echo "  1. Open: http://localhost:3000"
echo "  2. Click 'Login'"
echo "  3. Login with credentials above"
echo "=========================================="
