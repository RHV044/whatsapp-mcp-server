# Build stage
FROM golang:1.24-alpine AS builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev sqlite-dev

WORKDIR /app

# Copy go.mod and go.sum first (better layer caching)
COPY go.mod go.sum ./

# Copy source code
COPY main.go .
COPY scheduler/ ./scheduler/

# Download dependencies and update go.sum
RUN go mod tidy && go mod download

# Build the application with CGO enabled
RUN CGO_ENABLED=1 GOOS=linux go build -o whatsapp-bridge main.go

# Runtime stage
FROM alpine:latest

# Install runtime dependencies
RUN apk add --no-cache ca-certificates sqlite-libs

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/whatsapp-bridge .

# Create directory for WhatsApp data
RUN mkdir -p /app/data

# Expose the API port
EXPOSE 8080

# Run the bridge
CMD ["./whatsapp-bridge"]
