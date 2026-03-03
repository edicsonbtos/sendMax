#!/bin/bash
# Reemplazar con el token obtenido del login exitoso
TOKEN="TU_TOKEN_AQUI"
API_URL="https://sendmax11-production.up.railway.app"

echo "==================================="
echo "1. Intentar Login con datos CORRECTOS:"
echo "==================================="
curl -X POST "$API_URL/auth/operator/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "edicsonfront@gmail.com", "password": "tu_password_real"}'

echo -e "\n\n==================================="
echo "2. Intentar Acceder a Ruta Protegida (SIN TOKEN):"
echo "==================================="
curl -s -o /dev/null -w "%{http_code}" -X GET "$API_URL/api/operators/wallet/summary"
echo " <- Deberia ser 401"

echo -e "\n\n==================================="
echo "3. Intentar Acceder a Ruta Protegida (CON TOKEN):"
echo "==================================="
curl -X GET "$API_URL/api/operators/wallet/summary" \
     -H "Authorization: Bearer $TOKEN"
