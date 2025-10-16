FROM python:3.11-slim

# Install FFmpeg for audio conversion (optional but recommended)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies using UV
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Environment variables for HTTP/SSE mode
ENV MCP_TRANSPORT=http
ENV MCP_PORT=8301
ENV MCP_HOST=0.0.0.0
ENV PROXY_PORT=8300
ENV PROXY_HOST=0.0.0.0

# Expose OAuth Proxy port (8300) - this is what nginx will proxy to
EXPOSE 8300

# Run the start script that launches both OAuth proxy and MCP server
CMD ["./start.sh"]
