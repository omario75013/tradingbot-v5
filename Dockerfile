# TradingBot AI V5 Dockerfile
FROM python:3.11-slim

# Metadata
LABEL maintainer="TradingBot AI"
LABEL version="5.0.0"
LABEL description="AI-Powered Crypto Trading Bot with Arbitrage"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p logs models/current models/archive data

# Expose Prometheus metrics port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/metrics || exit 1

# Run the bot
CMD ["python", "main_v5.py", "--paper"]
