#!/bin/bash

# Script untuk testing API endpoints
# Ganti ACCESS_TOKEN dengan token yang valid dari SSO

# Konfigurasi
BASE_URL="http://127.0.0.1:8000/api"
ACCESS_TOKEN="your-access-token-here"

echo "======================================"
echo "NOC RAG POC - API Testing Script"
echo "======================================"
echo ""

if [ "$ACCESS_TOKEN" = "your-access-token-here" ]; then
    echo "ERROR: Ganti ACCESS_TOKEN di script ini dengan token yang valid!"
    echo ""
    echo "Cara mendapatkan token:"
    echo "curl -X POST https://sso.arnatech.id/api/auth/login/ \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"email\": \"your-email@arnatech.id\", \"password\": \"your-password\"}'"
    echo ""
    exit 1
fi

# Test 1: List documents
echo "Test 1: List documents"
echo "GET $BASE_URL/documents/"
curl -X GET "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json"
echo ""
echo ""

# Test 2: Upload document (jika ada sample file)
if [ -f "sample.txt" ]; then
    echo "Test 2: Upload document"
    echo "POST $BASE_URL/documents/"
    curl -X POST "$BASE_URL/documents/" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -F "file=@sample.txt" \
      -F "title=Sample Document"
    echo ""
    echo ""
fi

# Test 3: Simple chat
echo "Test 3: Simple chat"
echo "POST $BASE_URL/chat/"
curl -X POST "$BASE_URL/chat/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Halo, apa yang bisa kamu bantu?",
    "include_chart": false
  }'
echo ""
echo ""

# Test 4: Chat history
echo "Test 4: Chat history"
echo "GET $BASE_URL/chat/history"
curl -X GET "$BASE_URL/chat/history" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json"
echo ""
echo ""

echo "======================================"
echo "API Testing completed!"
echo "======================================"
