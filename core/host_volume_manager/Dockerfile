FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY host_volume_manager/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the host volume manager
COPY host_volume_manager.py .

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/scan_folders

# Expose port
EXPOSE 8011

# Run the host volume manager in serve mode
CMD ["python3", "host_volume_manager.py", "serve", "--port", "8011"] 