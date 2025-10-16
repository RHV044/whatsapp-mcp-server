# Claude Desktop Configuration for WhatsApp MCP

## 1. Download Claude Desktop
https://claude.ai/download

## 2. Create/Edit Configuration File

### Windows
Location: `%APPDATA%\Claude\claude_desktop_config.json`

### macOS/Linux  
Location: `~/.config/claude/claude_desktop_config.json`

## 3. Add This Configuration

```json
{
  "mcpServers": {
    "whatsapp": {
      "url": "https://rzdevquality.com:8443/messages",
      "transport": {
        "type": "http"
      }
    }
  }
}
```

## 4. Restart Claude Desktop

That's it! No OAuth needed, works directly.

## Benefits
- ✅ No OAuth required
- ✅ More stable than web interface
- ✅ Better performance
- ✅ Works offline for local servers
- ✅ Easier debugging

## If You Still Want Web

We can try:
1. Delete ALL existing MCP servers from Claude.ai web
2. Clear browser cache/cookies for claude.ai
3. Try incognito/private mode
4. Try different browser
5. Wait 24 hours (might be rate-limited)
