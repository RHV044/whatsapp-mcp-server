"""
OAuth 2.1 Proxy for WhatsApp MCP Server

This proxy handles OAuth 2.1 authentication and forwards authenticated requests
to the FastMCP server running on port 8300.
"""

from fastapi import FastAPI, Request, HTTPException, Form, Header
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional
import os
import uvicorn

# Configuration
SERVER_URL = os.environ.get('SERVER_URL', 'https://rzdevquality.com:8443')
MCP_BACKEND = os.environ.get('MCP_BACKEND', 'http://localhost:8301')

# OAuth Configuration
OAUTH_CLIENT_ID = os.environ.get('OAUTH_CLIENT_ID', 'whatsapp-mcp-client-rzdev')
OAUTH_CLIENT_SECRET = os.environ.get('OAUTH_CLIENT_SECRET', 'sk_whatsapp_mcp_2025_secure_secret_key_v1_production')

# In-memory storage (use Redis/DB in production)
oauth_codes = {}
oauth_tokens = {}
registered_clients = {}  # client_id -> {client_secret, client_name, redirect_uris, created_at}

app = FastAPI(title="WhatsApp MCP OAuth Proxy")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth 2.1 Discovery Endpoint
@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """OAuth 2.1 Authorization Server Metadata with Dynamic Client Registration"""
    return {
        "issuer": SERVER_URL,
        "authorization_endpoint": f"{SERVER_URL}/oauth/authorize",
        "token_endpoint": f"{SERVER_URL}/oauth/token",
        "registration_endpoint": f"{SERVER_URL}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
    }

# Dynamic Client Registration Endpoint (RFC 7591)
@app.post("/oauth/register")
async def register_client(request: Request):
    """OAuth 2.1 Dynamic Client Registration (RFC 7591)
    
    Allows Claude.ai to automatically register and obtain client credentials
    without manual configuration by the user.
    """
    try:
        body = await request.json()
        
        # Validate required fields
        redirect_uris = body.get("redirect_uris", [])
        if not redirect_uris:
            raise HTTPException(status_code=400, detail="redirect_uris is required")
        
        # Generate client credentials
        client_id = f"mcp-{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)
        
        # Store client registration
        registered_clients[client_id] = {
            "client_secret": client_secret,
            "client_name": body.get("client_name", "MCP Client"),
            "redirect_uris": redirect_uris,
            "grant_types": body.get("grant_types", ["authorization_code"]),
            "response_types": body.get("response_types", ["code"]),
            "token_endpoint_auth_method": body.get("token_endpoint_auth_method", "client_secret_post"),
            "created_at": datetime.now().isoformat()
        }
        
        print(f"✅ Registered new OAuth client: {client_id}")
        print(f"   Client Name: {body.get('client_name', 'MCP Client')}")
        print(f"   Redirect URIs: {redirect_uris}")
        
        # Return client credentials (RFC 7591 response)
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_id_issued_at": int(datetime.now().timestamp()),
            "client_secret_expires_at": 0,  # Never expires
            "redirect_uris": redirect_uris,
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post"
        }
        
    except Exception as e:
        print(f"❌ Error registering client: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# OAuth Authorization Endpoint
@app.get("/oauth/authorize")
async def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str
):
    """OAuth 2.1 Authorization Endpoint with PKCE"""
    # Validate client_id - accept both hardcoded and dynamically registered clients
    if client_id != OAUTH_CLIENT_ID and client_id not in registered_clients:
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    # Validate redirect_uri for dynamically registered clients
    if client_id in registered_clients:
        client_data = registered_clients[client_id]
        if redirect_uri not in client_data["redirect_uris"]:
            raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response_type")
    
    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Only S256 code_challenge_method is supported")
    
    # Generate authorization code
    auth_code = secrets.token_urlsafe(32)
    
    # Store authorization code
    oauth_codes[auth_code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "expires_at": datetime.now() + timedelta(minutes=10)
    }
    
    print(f"✅ Generated auth code for client {client_id}")
    
    # Redirect back with code
    return RedirectResponse(
        url=f"{redirect_uri}?code={auth_code}&state={state}",
        status_code=302
    )

# OAuth Token Endpoint
@app.post("/oauth/token")
async def token(
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    code_verifier: str = Form(...)
):
    """OAuth 2.1 Token Endpoint with PKCE"""
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="Unsupported grant_type")
    
    # Validate client credentials - support both hardcoded and dynamic clients
    valid_credentials = False
    if client_id == OAUTH_CLIENT_ID and client_secret == OAUTH_CLIENT_SECRET:
        valid_credentials = True
    elif client_id in registered_clients:
        if registered_clients[client_id]["client_secret"] == client_secret:
            valid_credentials = True
    
    if not valid_credentials:
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    
    if code not in oauth_codes:
        raise HTTPException(status_code=400, detail="Invalid authorization code")
    
    code_data = oauth_codes[code]
    
    if datetime.now() > code_data["expires_at"]:
        del oauth_codes[code]
        raise HTTPException(status_code=400, detail="Authorization code expired")
    
    if redirect_uri != code_data["redirect_uri"]:
        raise HTTPException(status_code=400, detail="Redirect URI mismatch")
    
    # Validate PKCE
    verifier_hash = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')
    
    if verifier_hash != code_data["code_challenge"]:
        raise HTTPException(status_code=400, detail="Invalid code_verifier")
    
    # Delete used code
    del oauth_codes[code]
    
    # Generate access token
    access_token = secrets.token_urlsafe(32)
    
    oauth_tokens[access_token] = {
        "client_id": client_id,
        "expires_at": datetime.now() + timedelta(hours=24)
    }
    
    print(f"✅ Issued access token for client {client_id}")
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 86400
    }

# Middleware to validate access token
async def validate_token(authorization: Optional[str] = Header(None)):
    """Validate Bearer token from Authorization header"""
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    if token not in oauth_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    token_data = oauth_tokens[token]
    
    if datetime.now() > token_data["expires_at"]:
        del oauth_tokens[token]
        raise HTTPException(status_code=401, detail="Token expired")
    
    return token_data

# Proxy MCP requests to backend
@app.api_route("/messages", methods=["GET", "POST", "OPTIONS"])
async def proxy_mcp(request: Request, authorization: Optional[str] = Header(None)):
    """Proxy authenticated requests to MCP backend"""
    
    # Validate OAuth token
    token_data = await validate_token(authorization)
    if not token_data:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    
    # Proxy request to MCP backend
    async with httpx.AsyncClient() as client:
        try:
            if request.method == "GET":
                response = await client.get(
                    f"{MCP_BACKEND}/messages",
                    headers=dict(request.headers),
                    timeout=30.0
                )
                
                if "text/event-stream" in response.headers.get("content-type", ""):
                    return StreamingResponse(
                        response.aiter_bytes(),
                        media_type="text/event-stream",
                        headers=dict(response.headers)
                    )
                else:
                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )
            
            elif request.method == "POST":
                body = await request.body()
                response = await client.post(
                    f"{MCP_BACKEND}/messages",
                    content=body,
                    headers=dict(request.headers),
                    timeout=30.0
                )
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            
            elif request.method == "OPTIONS":
                return Response(status_code=200)
                
        except httpx.RequestError as e:
            print(f"❌ Error proxying to MCP backend: {e}")
            raise HTTPException(status_code=502, detail="Backend unavailable")

if __name__ == "__main__":
    port = int(os.environ.get('PROXY_PORT', '8300'))
    host = os.environ.get('PROXY_HOST', '0.0.0.0')
    
    print("🔐 Starting OAuth 2.1 Proxy for WhatsApp MCP Server...")
    print(f"🌐 Proxy listening on http://{host}:{port}")
    print(f"📡 MCP Backend: {MCP_BACKEND}")
    print(f"🔑 OAuth Client ID: {OAUTH_CLIENT_ID}")
    print(f"🎫 OAuth Client Secret: {OAUTH_CLIENT_SECRET[:8]}...{OAUTH_CLIENT_SECRET[-4:]}")
    print(f"📍 Endpoints:")
    print(f"   - OAuth Discovery: /.well-known/oauth-authorization-server")
    print(f"   - OAuth Authorize: /oauth/authorize")
    print(f"   - OAuth Token: /oauth/token")
    print(f"   - MCP Messages: /messages")
    
    uvicorn.run(app, host=host, port=port)
