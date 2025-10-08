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

# Environment variables for HTTP/SSE mode
ENV MCP_TRANSPORT=http
ENV MCP_PORT=8300
ENV MCP_HOST=0.0.0.0

# Expose MCP server port for HTTP/SSE transport (8000-8999 range)
EXPOSE 8300

# Run the MCP server in HTTP mode by default
# Can be overridden to stdio mode by setting MCP_TRANSPORT=stdio
CMD ["python", "main.py"]
