# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8080

# Run FastAPI server with Uvicorn optimized for streaming WebSockets
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--ws", "websockets", "--timeout-keep-alive", "300"]
