# OAuth 2.1 Setup Instructions for Claude.ai

## OAuth Credentials

Use these credentials when configuring your MCP server in Claude.ai:

```
Client ID: whatsapp-mcp-client-rzdev
Client Secret: sk_whatsapp_mcp_2025_secure_secret_key_v1_production
```

## Configuration Steps

1. Go to https://claude.ai/settings/connectors

2. Find your "Whatsapp MCP" server

3. Click on "Edit" or "Configure OAuth Credentials"

4. Enter the credentials:
   - **OAuth Client ID**: `whatsapp-mcp-client-rzdev`
   - **OAuth Client Secret**: `sk_whatsapp_mcp_2025_secure_secret_key_v1_production`

5. Save the configuration

6. Try connecting again - Claude.ai should now:
   - Discover OAuth metadata at `https://rzdevquality.com:8443/.well-known/oauth-authorization-server`
   - Redirect to authorization endpoint
   - Exchange code for token
   - Connect to MCP server successfully

## OAuth Endpoints

- **Discovery**: `https://rzdevquality.com:8443/.well-known/oauth-authorization-server`
- **Authorization**: `https://rzdevquality.com:8443/oauth/authorize`
- **Token**: `https://rzdevquality.com:8443/oauth/token`
- **MCP Endpoint**: `https://rzdevquality.com:8443/messages`

## Security Notes

- This implementation uses OAuth 2.1 with PKCE (Proof Key for Code Exchange)
- Authorization codes expire after 10 minutes
- Access tokens expire after 24 hours
- Tokens are stored in-memory (for production, use Redis or a database)

## Testing OAuth Flow

You can test the OAuth discovery endpoint:

```bash
curl https://rzdevquality.com:8443/.well-known/oauth-authorization-server
```

Expected response:
```json
{
  "issuer": "https://rzdevquality.com:8443",
  "authorization_endpoint": "https://rzdevquality.com:8443/oauth/authorize",
  "token_endpoint": "https://rzdevquality.com:8443/oauth/token",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code"],
  "code_challenge_methods_supported": ["S256"],
  "token_endpoint_auth_methods_supported": ["client_secret_post"]
}
```
