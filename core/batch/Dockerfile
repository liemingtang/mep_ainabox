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

# Copy requirements from batch (core is build context) and install dependencies
COPY batch/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy batch files into /app
COPY batch/ ./

# Also copy the processors used by the worker into expected paths
RUN mkdir -p /app/processors/text_processor /app/processors/embedding_processor
COPY processors/text_processor/batch_text_processor.py /app/processors/text_processor/batch_text_processor.py
COPY processors/embedding_processor/batch_embedding_processor.py /app/processors/embedding_processor/batch_embedding_processor.py

# Create a non-root user for security
RUN useradd -m -u 1000 scanner && \
    chown -R scanner:scanner /app

# Switch to non-root user
USER scanner

# Set the entrypoint
ENTRYPOINT ["python3"] 