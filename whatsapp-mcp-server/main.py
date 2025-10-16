from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
import requests
import os
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
import sys

# Configuration from environment variables or defaults
BRIDGE_BASE_URL = os.environ.get('WHATSAPP_BRIDGE_URL', 'http://localhost:8080')

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
        # HTTP Streamable mode with OAuth 2.1
        print("🌐 Starting MCP Server with OAuth 2.1 in HTTP Streamable mode...")
        print(f"📡 Bridge URL: {BRIDGE_BASE_URL}")
        print(f"🔐 OAuth Client ID: {OAUTH_CLIENT_ID}")
        print(f"🔑 OAuth Client Secret: {OAUTH_CLIENT_SECRET[:8]}...{OAUTH_CLIENT_SECRET[-4:]}")
        
        # Create FastAPI app for OAuth endpoints
        app = FastAPI(title="WhatsApp MCP Server with OAuth 2.1")
        
        # Add CORS middleware
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
            """OAuth 2.1 Authorization Server Metadata"""
            return {
                "issuer": SERVER_URL,
                "authorization_endpoint": f"{SERVER_URL}/oauth/authorize",
                "token_endpoint": f"{SERVER_URL}/oauth/token",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": ["client_secret_post"],
            }
        
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
            # Validate client_id
            if client_id != OAUTH_CLIENT_ID:
                raise HTTPException(status_code=400, detail="Invalid client_id")
            
            # Validate response_type
            if response_type != "code":
                raise HTTPException(status_code=400, detail="Unsupported response_type")
            
            # Validate PKCE
            if code_challenge_method != "S256":
                raise HTTPException(status_code=400, detail="Only S256 code_challenge_method is supported")
            
            # Generate authorization code
            auth_code = secrets.token_urlsafe(32)
            
            # Store authorization code with PKCE challenge
            oauth_codes[auth_code] = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": code_challenge,
                "expires_at": datetime.now() + timedelta(minutes=10)
            }
            
            # Redirect back to client with code
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
            # Validate grant_type
            if grant_type != "authorization_code":
                raise HTTPException(status_code=400, detail="Unsupported grant_type")
            
            # Validate client credentials
            if client_id != OAUTH_CLIENT_ID or client_secret != OAUTH_CLIENT_SECRET:
                raise HTTPException(status_code=401, detail="Invalid client credentials")
            
            # Validate authorization code
            if code not in oauth_codes:
                raise HTTPException(status_code=400, detail="Invalid authorization code")
            
            code_data = oauth_codes[code]
            
            # Check expiration
            if datetime.now() > code_data["expires_at"]:
                del oauth_codes[code]
                raise HTTPException(status_code=400, detail="Authorization code expired")
            
            # Validate redirect_uri matches
            if redirect_uri != code_data["redirect_uri"]:
                raise HTTPException(status_code=400, detail="Redirect URI mismatch")
            
            # Validate PKCE code_verifier
            verifier_hash = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            
            if verifier_hash != code_data["code_challenge"]:
                raise HTTPException(status_code=400, detail="Invalid code_verifier")
            
            # Delete used authorization code
            del oauth_codes[code]
            
            # Generate access token
            access_token = secrets.token_urlsafe(32)
            
            # Store access token
            oauth_tokens[access_token] = {
                "client_id": client_id,
                "expires_at": datetime.now() + timedelta(hours=24)
            }
            
            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 86400  # 24 hours
            }
        
        # Mount FastMCP's HTTP Streamable endpoint
        # We need to get the ASGI app from FastMCP
        port = int(os.environ.get('MCP_PORT', '8300'))
        host = os.environ.get('MCP_HOST', '0.0.0.0')
        
        # Configure FastMCP settings for HTTP mode
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.settings.streamable_http_path = "/messages"
        
        # Get FastMCP's ASGI app and mount it
        from mcp.server.fastmcp.server import create_app_streamable
        mcp_app = create_app_streamable(mcp)
        
        # Mount MCP app under /messages
        app.mount("/messages", mcp_app)
        
        print(f"✅ Server ready to start on http://{host}:{port}")
        print(f"📍 MCP endpoint: http://{host}:{port}/messages")
        print(f"� OAuth discovery: http://{host}:{port}/.well-known/oauth-authorization-server")
        print(f"� OAuth authorize: http://{host}:{port}/oauth/authorize")
        print(f"🎫 OAuth token: http://{host}:{port}/oauth/token")
        
        # Run with uvicorn
        uvicorn.run(app, host=host, port=port)
    
    else:
        # stdio mode for local access
        print("💻 Starting MCP Server in stdio mode...")
        print(f"📡 Bridge URL: {BRIDGE_BASE_URL}")
        mcp.run(transport='stdio')
