FROM python:3.10-slim

WORKDIR /app

# Copy the Qdrant UI files
COPY . .

# Expose the port
EXPOSE 7070

# Start the server
CMD ["python3", "server.py"] 