FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libpq-dev \
    gcc \
    curl \
    gnupg \
    lsb-release

# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the scanner scripts
COPY folder_scanner.py .
COPY queue_file_processing.py .
COPY process_file_processing_queue.py .
COPY text_processor.py .
COPY batch_process_file_queue.py .
COPY check_queue.py .
COPY test_file_paths.py .
COPY test_db.py .
COPY test_elasticsearch.py .

# Create a non-root user for security
RUN useradd -m -u 1000 scanner && \
    chown -R scanner:scanner /app

# Switch to non-root user
USER scanner

# Set the entrypoint
ENTRYPOINT ["python3", "folder_scanner.py"] 