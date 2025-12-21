#!/bin/bash

echo "Getting admin access token..."
RESPONSE=$(curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" \
  -d "client_id=admin-cli")

TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Failed to get admin token. Is Keycloak running?"
  echo "Response: $RESPONSE"
  exit 1
fi

echo "Creating realm 'rag-system'..."

RESULT=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8080/admin/realms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "realm": "rag-system",
    "enabled": true,
    "displayName": "RAG System",
    "loginTheme": "keycloak",
    "registrationAllowed": false,
    "resetPasswordAllowed": true,
    "rememberMe": true,
    "sslRequired": "none"
  }')

HTTP_CODE=$(echo "$RESULT" | tail -n1)

if [ "$HTTP_CODE" = "201" ]; then
  echo "✓ Realm 'rag-system' created successfully!"
elif [ "$HTTP_CODE" = "409" ]; then
  echo "✓ Realm 'rag-system' already exists!"
else
  echo "Error creating realm. HTTP Code: $HTTP_CODE"
  echo "$RESULT"
  exit 1
fi

echo ""
echo "Realm is ready! Now reload: http://localhost:3000"
