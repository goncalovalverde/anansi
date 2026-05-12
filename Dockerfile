# Multi-stage build for Anansi dashboard
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend-vue
COPY frontend-vue/package*.json ./
RUN npm ci
COPY frontend-vue .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend backend/
COPY log_config.yaml .

# Copy frontend build from builder stage
COPY --from=frontend-builder /app/frontend-vue/dist frontend-vue/dist

# Create data directory for persistence
RUN mkdir -p /app/data

# Expose port 9000
EXPOSE 9000

# Volume for persistent database storage
VOLUME ["/app/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/api/health')" || exit 1

# Run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "9000"]
