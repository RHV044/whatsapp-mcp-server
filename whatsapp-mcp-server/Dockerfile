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

# Expose MCP server port (if needed for stdio communication)
# MCP typically uses stdio, but we can expose a port for future HTTP transport
EXPOSE 3000

# Run the MCP server
CMD ["python", "main.py"]
