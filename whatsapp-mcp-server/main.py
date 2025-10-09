from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
import requests
import os
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media,
    dataclass_to_dict
)

# Configuration from environment variables or defaults
BRIDGE_BASE_URL = os.environ.get('WHATSAPP_BRIDGE_URL', 'http://localhost:8080')

# OAuth Configuration
OAUTH_ENABLED = os.environ.get('OAUTH_ENABLED', 'false').lower() == 'true'
SERVER_BASE_URL = os.environ.get('SERVER_BASE_URL', 'https://rzdevquality.com:8443')
OAUTH_ISSUER = os.environ.get('OAUTH_ISSUER', SERVER_BASE_URL)

# Simple in-memory storage for OAuth (for production, use Redis or database)
oauth_clients = {}
oauth_tokens = {}
oauth_codes = {}

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.
    
    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return contacts

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_jid, include_last_message)
    return dataclass_to_dict(chat)

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return dataclass_to_dict(chat)

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact.
    
    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        jid: The JID of the contact to search for
    """
    message = whatsapp_get_last_interaction(jid)
    return message

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    # Convert MessageContext to dict, including nested Message objects
    result = dataclass_to_dict(context)
    if result and 'message' in result:
        result['message'] = dataclass_to_dict(context.message)
    if result and 'before' in result:
        result['before'] = [dataclass_to_dict(msg) for msg in context.before]
    if result and 'after' in result:
        result['after'] = [dataclass_to_dict(msg) for msg in context.after]
    return result

@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the whatsapp_send_message function with the unified recipient parameter
    success, status_message = whatsapp_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient. For group messages use the JID.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the media file to send (image, video, document)
    
    Returns:
        A dictionary containing success status and a status message
    """
    
    # Call the whatsapp_send_file function
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient. For group messages use the JID. If it errors due to ffmpeg not being installed, use send_file instead.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the audio file to send (will be converted to Opus .ogg if it's not a .ogg file)
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)
    
    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

@mcp.tool()
def schedule_message(
    recipient: str,
    message: str,
    scheduled_time: str,
    check_for_response: bool = True
) -> Dict[str, Any]:
    """Schedule a WhatsApp message to be sent in the future.
    
    The message will only be sent at the specified time if the condition is met.
    By default (check_for_response=True), the message will be automatically paused
    if the recipient sends any message after this scheduled message is created.
    
    Args:
        recipient: Phone number with country code (no + or symbols) or JID 
                  (e.g., "1234567890" or "1234567890@s.whatsapp.net")
        message: The message text to send
        scheduled_time: ISO-8601 formatted datetime when to send the message 
                       (e.g., "2025-10-06T15:30:00Z" or "2025-10-06T15:30:00-03:00")
        check_for_response: If True, the message will be paused if the recipient 
                           sends a message after scheduling (default: True)
    
    Returns:
        A dictionary with success status and the scheduled message details
    
    Example:
        schedule_message(
            recipient="5491156543944",
            message="Hi! Just checking in",
            scheduled_time="2025-10-06T15:00:00Z",
            check_for_response=True
        )
    """
    try:
        response = requests.post(
            f"{BRIDGE_BASE_URL}/api/schedule",
            json={
                "recipient": recipient,
                "message": message,
                "scheduled_time": scheduled_time,
                "check_for_response": check_for_response
            },
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Failed to schedule message: {str(e)}"
        }

@mcp.tool()
def list_scheduled_messages(
    status: Optional[str] = None,
    recipient: Optional[str] = None
) -> Dict[str, Any]:
    """List all scheduled messages with optional filters.
    
    Args:
        status: Filter by status. Options: "pending", "sent", "paused", "cancelled", "failed"
        recipient: Filter by recipient phone number or JID
    
    Returns:
        A dictionary with success status and a list of scheduled messages
    
    Example:
        # Get all pending messages
        list_scheduled_messages(status="pending")
        
        # Get all messages for a specific contact
        list_scheduled_messages(recipient="5491156543944")
    """
    try:
        params = {}
        if status:
            params["status"] = status
        if recipient:
            params["recipient"] = recipient
        
        response = requests.get(
            f"{BRIDGE_BASE_URL}/api/scheduled",
            params=params,
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Failed to list scheduled messages: {str(e)}",
            "messages": []
        }

@mcp.tool()
def get_scheduled_message(message_id: str) -> Dict[str, Any]:
    """Get details of a specific scheduled message.
    
    Args:
        message_id: The ID of the scheduled message
    
    Returns:
        A dictionary with the scheduled message details
    """
    try:
        response = requests.get(
            f"{BRIDGE_BASE_URL}/api/scheduled/{message_id}",
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Failed to get scheduled message: {str(e)}"
        }

@mcp.tool()
def cancel_scheduled_message(message_id: str) -> Dict[str, Any]:
    """Cancel a scheduled message before it's sent.
    
    This permanently cancels the message. It cannot be resumed after cancellation.
    
    Args:
        message_id: The ID of the scheduled message to cancel
    
    Returns:
        A dictionary with success status
    
    Example:
        cancel_scheduled_message("abc-123-def-456")
    """
    try:
        response = requests.delete(
            f"{BRIDGE_BASE_URL}/api/scheduled/{message_id}",
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Failed to cancel message: {str(e)}"
        }

@mcp.tool()
def pause_scheduled_message(message_id: str) -> Dict[str, Any]:
    """Pause a pending scheduled message.
    
    A paused message will not be sent at its scheduled time. It can be resumed later.
    
    Args:
        message_id: The ID of the scheduled message to pause
    
    Returns:
        A dictionary with success status
    
    Example:
        pause_scheduled_message("abc-123-def-456")
    """
    try:
        response = requests.patch(
            f"{BRIDGE_BASE_URL}/api/scheduled/{message_id}",
            json={"action": "pause"},
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Failed to pause message: {str(e)}"
        }

@mcp.tool()
def resume_scheduled_message(message_id: str) -> Dict[str, Any]:
    """Resume a paused scheduled message.
    
    The message will be sent at its originally scheduled time if that time hasn't passed yet.
    If the scheduled time has passed, it will be sent immediately.
    
    Args:
        message_id: The ID of the scheduled message to resume
    
    Returns:
        A dictionary with success status
    
    Example:
        resume_scheduled_message("abc-123-def-456")
    """
    try:
        response = requests.patch(
            f"{BRIDGE_BASE_URL}/api/scheduled/{message_id}",
            json={"action": "resume"},
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Failed to resume message: {str(e)}"
        }

if __name__ == "__main__":
    import sys
    import asyncio
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import Response, JSONResponse, RedirectResponse
    from starlette.requests import Request
    import uvicorn
    import json
    
    # Check if running in HTTP mode or stdio mode
    mode = os.environ.get('MCP_TRANSPORT', 'stdio').lower()
    
    # Allow command line override
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--http']:
            mode = 'http'
        elif sys.argv[1] == '--stdio':
            mode = 'stdio'
    
    if mode == 'http':
        # HTTP Streamable mode for remote access with OAuth 2.1
        print("🌐 Starting MCP Server in HTTP Streamable mode...")
        print(f"📡 Bridge URL: {BRIDGE_BASE_URL}")
        print(f"🔒 OAuth enabled: {OAUTH_ENABLED}")
        
        # OAuth 2.1 Helper Functions
        def generate_token():
            """Generate a secure random token"""
            return secrets.token_urlsafe(32)
        
        def verify_token(token: str, expected_audience: str) -> Optional[Dict]:
            """Verify and return token data if valid"""
            if token in oauth_tokens:
                token_data = oauth_tokens[token]
                if token_data['expires_at'] > datetime.now():
                    if token_data.get('resource') == expected_audience:
                        return token_data
                else:
                    del oauth_tokens[token]
            return None
        
        def extract_bearer_token(authorization: str) -> Optional[str]:
            """Extract Bearer token from Authorization header"""
            if authorization and authorization.startswith('Bearer '):
                return authorization[7:]
            return None
        
        # OAuth Endpoints
        async def handle_well_known_oauth_protected_resource(request):
            """RFC 9728 - Protected Resource Metadata"""
            metadata = {
                "resource": SERVER_BASE_URL,
                "authorization_servers": [OAUTH_ISSUER]
            }
            return JSONResponse(metadata)
        
        async def handle_well_known_oauth_authorization_server(request):
            """RFC 8414 - Authorization Server Metadata"""
            metadata = {
                "issuer": OAUTH_ISSUER,
                "authorization_endpoint": f"{SERVER_BASE_URL}/oauth/authorize",
                "token_endpoint": f"{SERVER_BASE_URL}/oauth/token",
                "registration_endpoint": f"{SERVER_BASE_URL}/oauth/register",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
                "code_challenge_methods_supported": ["S256"],
                "revocation_endpoint": f"{SERVER_BASE_URL}/oauth/revoke",
                "scopes_supported": ["whatsapp:read", "whatsapp:write"]
            }
            return JSONResponse(metadata)
        
        async def handle_oauth_register(request):
            """RFC 7591 - Dynamic Client Registration"""
            try:
                body = await request.json()
                client_id = generate_token()
                client_secret = generate_token() if body.get('token_endpoint_auth_method') != 'none' else None
                
                client_data = {
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'redirect_uris': body.get('redirect_uris', []),
                    'client_name': body.get('client_name', 'Unknown Client'),
                    'grant_types': body.get('grant_types', ['authorization_code', 'refresh_token']),
                    'created_at': datetime.now()
                }
                
                oauth_clients[client_id] = client_data
                
                response_data = {
                    'client_id': client_id,
                    'client_id_issued_at': int(client_data['created_at'].timestamp()),
                    'client_name': client_data['client_name'],
                    'redirect_uris': client_data['redirect_uris'],
                    'grant_types': client_data['grant_types'],
                    'token_endpoint_auth_method': 'client_secret_post' if client_secret else 'none'
                }
                
                if client_secret:
                    response_data['client_secret'] = client_secret
                
                print(f"✅ Registered new OAuth client: {client_data['client_name']} ({client_id})")
                return JSONResponse(response_data, status_code=201)
            except Exception as e:
                print(f"❌ Client registration failed: {e}")
                return JSONResponse({'error': 'invalid_request', 'error_description': str(e)}, status_code=400)
        
        async def handle_oauth_authorize(request):
            """OAuth Authorization Endpoint"""
            client_id = request.query_params.get('client_id')
            redirect_uri = request.query_params.get('redirect_uri')
            state = request.query_params.get('state')
            code_challenge = request.query_params.get('code_challenge')
            code_challenge_method = request.query_params.get('code_challenge_method', 'S256')
            resource = request.query_params.get('resource')
            
            if client_id not in oauth_clients:
                return JSONResponse({'error': 'invalid_client'}, status_code=400)
            
            client = oauth_clients[client_id]
            
            if redirect_uri not in client['redirect_uris']:
                return JSONResponse({'error': 'invalid_redirect_uri'}, status_code=400)
            
            # Auto-approve (in production, show consent screen)
            code = generate_token()
            oauth_codes[code] = {
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'code_challenge': code_challenge,
                'code_challenge_method': code_challenge_method,
                'resource': resource or SERVER_BASE_URL,
                'expires_at': datetime.now() + timedelta(minutes=10),
                'used': False
            }
            
            callback_url = f"{redirect_uri}?code={code}"
            if state:
                callback_url += f"&state={state}"
            
            print(f"✅ Authorization code issued for client {client_id}")
            return RedirectResponse(callback_url)
        
        async def handle_oauth_token(request):
            """OAuth Token Endpoint"""
            try:
                body = await request.form()
                grant_type = body.get('grant_type')
                
                if grant_type == 'authorization_code':
                    code = body.get('code')
                    client_id = body.get('client_id')
                    code_verifier = body.get('code_verifier')
                    resource = body.get('resource')
                    
                    if code not in oauth_codes:
                        return JSONResponse({'error': 'invalid_grant'}, status_code=400)
                    
                    code_data = oauth_codes[code]
                    
                    if code_data['used'] or code_data['expires_at'] < datetime.now():
                        return JSONResponse({'error': 'invalid_grant'}, status_code=400)
                    
                    if code_data['client_id'] != client_id:
                        return JSONResponse({'error': 'invalid_client'}, status_code=400)
                    
                    # Validate PKCE
                    if code_data.get('code_challenge'):
                        if not code_verifier:
                            return JSONResponse({'error': 'invalid_request', 'error_description': 'code_verifier required'}, status_code=400)
                        
                        if code_data['code_challenge_method'] == 'S256':
                            verifier_hash = base64.urlsafe_b64encode(
                                hashlib.sha256(code_verifier.encode()).digest()
                            ).decode().rstrip('=')
                            
                            if verifier_hash != code_data['code_challenge']:
                                return JSONResponse({'error': 'invalid_grant', 'error_description': 'PKCE validation failed'}, status_code=400)
                    
                    code_data['used'] = True
                    
                    # Generate tokens
                    access_token = generate_token()
                    refresh_token = generate_token()
                    
                    token_resource = resource or code_data['resource']
                    
                    oauth_tokens[access_token] = {
                        'client_id': client_id,
                        'token_type': 'Bearer',
                        'resource': token_resource,
                        'scope': 'whatsapp:read whatsapp:write',
                        'expires_at': datetime.now() + timedelta(hours=1),
                        'refresh_token': refresh_token
                    }
                    
                    oauth_tokens[refresh_token] = {
                        'client_id': client_id,
                        'token_type': 'refresh_token',
                        'resource': token_resource,
                        'access_token': access_token,
                        'expires_at': datetime.now() + timedelta(days=30)
                    }
                    
                    print(f"✅ Access token issued for client {client_id}")
                    return JSONResponse({
                        'access_token': access_token,
                        'token_type': 'Bearer',
                        'expires_in': 3600,
                        'refresh_token': refresh_token,
                        'scope': 'whatsapp:read whatsapp:write'
                    })
                
                elif grant_type == 'refresh_token':
                    refresh_token = body.get('refresh_token')
                    resource = body.get('resource')
                    
                    if refresh_token not in oauth_tokens:
                        return JSONResponse({'error': 'invalid_grant'}, status_code=400)
                    
                    refresh_data = oauth_tokens[refresh_token]
                    
                    if refresh_data['expires_at'] < datetime.now():
                        return JSONResponse({'error': 'invalid_grant'}, status_code=400)
                    
                    old_access_token = refresh_data.get('access_token')
                    if old_access_token and old_access_token in oauth_tokens:
                        del oauth_tokens[old_access_token]
                    
                    new_access_token = generate_token()
                    new_refresh_token = generate_token()
                    
                    token_resource = resource or refresh_data['resource']
                    
                    oauth_tokens[new_access_token] = {
                        'client_id': refresh_data['client_id'],
                        'token_type': 'Bearer',
                        'resource': token_resource,
                        'scope': 'whatsapp:read whatsapp:write',
                        'expires_at': datetime.now() + timedelta(hours=1),
                        'refresh_token': new_refresh_token
                    }
                    
                    oauth_tokens[new_refresh_token] = {
                        'client_id': refresh_data['client_id'],
                        'token_type': 'refresh_token',
                        'resource': token_resource,
                        'access_token': new_access_token,
                        'expires_at': datetime.now() + timedelta(days=30)
                    }
                    
                    del oauth_tokens[refresh_token]
                    
                    print(f"✅ Token refreshed for client {refresh_data['client_id']}")
                    return JSONResponse({
                        'access_token': new_access_token,
                        'token_type': 'Bearer',
                        'expires_in': 3600,
                        'refresh_token': new_refresh_token,
                        'scope': 'whatsapp:read whatsapp:write'
                    })
                
                else:
                    return JSONResponse({'error': 'unsupported_grant_type'}, status_code=400)
                    
            except Exception as e:
                print(f"❌ Token endpoint error: {e}")
                return JSONResponse({'error': 'server_error', 'error_description': str(e)}, status_code=500)
        
        # Authentication Middleware
        async def require_auth(request: Request):
            """Check OAuth authentication"""
            if not OAUTH_ENABLED:
                return None
            
            authorization = request.headers.get('Authorization')
            
            if not authorization:
                return Response(
                    status_code=401,
                    headers={
                        'WWW-Authenticate': f'Bearer realm="{SERVER_BASE_URL}", resource="{SERVER_BASE_URL}/.well-known/oauth-protected-resource"'
                    },
                    content=json.dumps({"error": "unauthorized", "error_description": "Authorization header required"})
                )
            
            token = extract_bearer_token(authorization)
            if not token:
                return Response(
                    status_code=401,
                    headers={'WWW-Authenticate': f'Bearer realm="{SERVER_BASE_URL}", error="invalid_token"'},
                    content=json.dumps({"error": "invalid_token", "error_description": "Invalid authorization header format"})
                )
            
            token_data = verify_token(token, SERVER_BASE_URL)
            if not token_data:
                return Response(
                    status_code=401,
                    headers={'WWW-Authenticate': f'Bearer realm="{SERVER_BASE_URL}", error="invalid_token"'},
                    content=json.dumps({"error": "invalid_token", "error_description": "Token is invalid or expired"})
                )
            
            request.state.token_data = token_data
            return None
        
        # MCP Endpoints (HTTP Streamable)
        async def handle_mcp_messages(request):
            """HTTP Streamable transport for MCP - handles JSON-RPC requests"""
            auth_error = await require_auth(request)
            if auth_error:
                return auth_error
            
            try:
                body = await request.json()
                
                # Basic JSON-RPC 2.0 response
                # TODO: Integrate with FastMCP's actual HTTP handler
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "resources": {},
                            "prompts": {}
                        },
                        "serverInfo": {
                            "name": "whatsapp",
                            "version": "1.0.0"
                        }
                    },
                    "id": body.get("id")
                })
            except Exception as e:
                print(f"❌ MCP request error: {e}")
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    },
                    "id": None
                }, status_code=500)
        
        async def handle_health(request):
            """Health check endpoint (no auth required)"""
            return JSONResponse({
                "status": "healthy",
                "mode": "http_streamable",
                "oauth_enabled": OAUTH_ENABLED,
                "timestamp": datetime.now().isoformat()
            })
        
        # Create Starlette app
        routes = [
            # OAuth 2.1 endpoints
            Route("/.well-known/oauth-protected-resource", endpoint=handle_well_known_oauth_protected_resource),
            Route("/.well-known/oauth-authorization-server", endpoint=handle_well_known_oauth_authorization_server),
            Route("/oauth/register", endpoint=handle_oauth_register, methods=["POST"]),
            Route("/oauth/authorize", endpoint=handle_oauth_authorize),
            Route("/oauth/token", endpoint=handle_oauth_token, methods=["POST"]),
            
            # MCP endpoints
            Route("/messages", endpoint=handle_mcp_messages, methods=["POST"]),
            Route("/health", endpoint=handle_health),
        ]
        
        app = Starlette(debug=True, routes=routes)
        
        port = int(os.environ.get('MCP_PORT', '8300'))
        host = os.environ.get('MCP_HOST', '0.0.0.0')
        
        print(f"✅ Server ready on http://{host}:{port}")
        print(f"📍 MCP endpoint: http://{host}:{port}/messages")
        print(f"🔐 OAuth authorize: {SERVER_BASE_URL}/oauth/authorize")
        print(f"🎫 OAuth token: {SERVER_BASE_URL}/oauth/token")
        print(f"📝 OAuth register: {SERVER_BASE_URL}/oauth/register")
        print(f"💚 Health check: http://{host}:{port}/health")
        
        uvicorn.run(app, host=host, port=port, log_level="info")
    
    else:
        # stdio mode for local access
        print("💻 Starting MCP Server in stdio mode...")
        print(f"📡 Bridge URL: {BRIDGE_BASE_URL}")
        mcp.run(transport='stdio')