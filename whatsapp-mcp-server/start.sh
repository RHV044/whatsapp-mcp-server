#!/bin/bash

# Start OAuth Proxy in background on port 8300
echo "🔐 Starting OAuth 2.1 Proxy on port 8300..."
MCP_BACKEND=http://localhost:8301 \
PROXY_PORT=8300 \
PROXY_HOST=0.0.0.0 \
SERVER_URL=${SERVER_URL:-https://rzdevquality.com:8443} \
OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID:-whatsapp-mcp-client-rzdev} \
OAUTH_CLIENT_SECRET=${OAUTH_CLIENT_SECRET:-sk_whatsapp_mcp_2025_secure_secret_key_v1_production} \
python -u oauth_proxy.py &

PROXY_PID=$!
echo "✅ OAuth Proxy started with PID $PROXY_PID"

# Give proxy time to start
sleep 2

# Start MCP Server on port 8301
echo "🌐 Starting MCP Server on port 8301..."
MCP_PORT=8301 \
MCP_HOST=0.0.0.0 \
MCP_TRANSPORT=http \
WHATSAPP_BRIDGE_URL=${WHATSAPP_BRIDGE_URL:-http://whatsapp-bridge:8080} \
python -u main.py --http &

MCP_PID=$!
echo "✅ MCP Server started with PID $MCP_PID"

# Wait for both processes
wait $PROXY_PID $MCP_PID
