#!/bin/bash

# Test script for nginx reverse proxy
echo "Testing nginx reverse proxy..."

# Test nginx health endpoint
echo "1. Testing nginx health endpoint..."
curl -f http://localhost/health
if [ $? -eq 0 ]; then
    echo "✅ Nginx is healthy"
else
    echo "❌ Nginx health check failed"
fi

# Test API health via proxy
echo -e "\n2. Testing API health via nginx proxy..."
curl -f http://localhost/api/health
if [ $? -eq 0 ]; then
    echo "✅ API health check via proxy successful"
else
    echo "❌ API health check via proxy failed"
fi

# Test CORS headers
echo -e "\n3. Testing CORS headers..."
curl -H "Origin: http://localhost" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     -v http://localhost/api/health 2>&1 | grep -i "access-control"
if [ $? -eq 0 ]; then
    echo "✅ CORS headers are present"
else
    echo "❌ CORS headers not found"
fi

# Test frontend via proxy
echo -e "\n4. Testing frontend via nginx proxy..."
curl -f http://localhost/ | head -n 5
if [ $? -eq 0 ]; then
    echo "✅ Frontend accessible via proxy"
else
    echo "❌ Frontend not accessible via proxy"
fi

# Test direct API access (should still work)
echo -e "\n5. Testing direct API access..."
curl -f http://localhost:8000/health
if [ $? -eq 0 ]; then
    echo "✅ Direct API access still works"
else
    echo "❌ Direct API access failed"
fi

echo -e "\nProxy test completed!"

