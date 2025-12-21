#!/bin/bash

# Quick diagnostic script to check Keycloak status
echo "=========================================="
echo "Keycloak Diagnostic Check"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
echo -n "1. Docker installed: "
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Docker not found${NC}"
    exit 1
fi

# Check Docker Compose
echo -n "2. Docker Compose installed: "
if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Docker Compose not found${NC}"
    exit 1
fi

# Check if Keycloak container exists
echo -n "3. Keycloak container exists: "
if docker-compose ps -q keycloak &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Container not found${NC}"
    echo "   Run: docker-compose up keycloak -d"
    exit 1
fi

# Check if Keycloak is running
echo -n "4. Keycloak container running: "
KEYCLOAK_STATE=$(docker-compose ps keycloak | grep -i "up" || true)
if [ -n "$KEYCLOAK_STATE" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Container not running${NC}"
    echo "   Run: docker-compose up keycloak -d"
    exit 1
fi

# Check if Keycloak port is accessible
echo -n "5. Keycloak responding on port 8080: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 2>/dev/null || echo "000")
if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 500 ]; then
    echo -e "${GREEN}✓${NC} (HTTP $HTTP_CODE)"
else
    echo -e "${RED}✗ Not responding${NC}"
    echo "   Keycloak may still be starting. Wait 30-60 seconds."
    echo "   Check logs: docker-compose logs keycloak"
    exit 1
fi

# Check if realm exists
echo -n "6. Checking realm 'rag-system': "
REALM_CHECK=$(curl -s http://localhost:8080/realms/rag-system/.well-known/openid-configuration 2>/dev/null | grep -o "rag-system" || echo "")
if [ -n "$REALM_CHECK" ]; then
    echo -e "${GREEN}✓ Realm configured${NC}"
else
    echo -e "${YELLOW}⚠ Realm not found or not configured${NC}"
    echo "   Follow KEYCLOAK_SETUP.md to create realm"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Keycloak Status: Running${NC}"
echo "=========================================="
echo ""
echo "Quick Links:"
echo "  • Keycloak Admin: http://localhost:8080"
echo "  • Realm info: http://localhost:8080/realms/rag-system"
echo ""
echo "Next Steps:"
if [ -z "$REALM_CHECK" ]; then
    echo "  1. Configure Keycloak realm (see KEYCLOAK_SETUP.md)"
    echo "  2. Update .env with client secret"
    echo "  3. Restart frontend: cd frontend && npm run dev"
else
    echo "  1. Open frontend: http://localhost:3000"
    echo "  2. Click 'Login' and authenticate"
fi
echo ""
