# Transaction Monitor Dockerfile
# Support multi-platform builds for M1 Mac
ARG BUILDPLATFORM
ARG TARGETPLATFORM
FROM --platform=${TARGETPLATFORM:-linux/amd64} python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash monitor-user
RUN chown -R monitor-user:monitor-user /app
USER monitor-user

# Run the application
CMD ["python", "transaction_monitor.py"]
