# Build Go service
FROM golang:1.18-alpine as go-builder
WORKDIR /go/src
COPY go-service /go/src
RUN go build -o /go/bin/infrakit-go-service

# Build Python environment
FROM python:3.9-slim

# Install system dependencies (if needed for psycopg2, redis, etc.)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy Go binary
COPY --from=go-builder /go/bin/infrakit-go-service /usr/local/bin/

# Copy application code
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port if needed (optional, e.g., 8080)
# EXPOSE 8080

# Set entrypoint
ENTRYPOINT ["python", "-m", "cli.main"]