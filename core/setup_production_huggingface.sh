#!/bin/bash

# Production Setup Script for HuggingFace Embeddings
# This script configures the production system to use HuggingFace as the default embedding provider

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "This script configures the production system to use HuggingFace as the default embedding provider."
    echo ""
    echo "Options:"
    echo "  --skip-ollama          Skip starting Ollama service (useful if you don't need it)"
    echo "  --init-models          Initialize HuggingFace models after setup"
    echo "  --test                 Run tests after setup"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                     # Full setup with Ollama"
    echo "  $0 --skip-ollama       # Setup without Ollama"
    echo "  $0 --init-models       # Setup and initialize models"
    echo "  $0 --test              # Setup and run tests"
}

# Parse command line arguments
SKIP_OLLAMA=false
INIT_MODELS=false
RUN_TESTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-ollama)
            SKIP_OLLAMA=true
            shift
            ;;
        --init-models)
            INIT_MODELS=true
            shift
            ;;
        --test)
            RUN_TESTS=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            echo "Unknown argument: $1"
            show_usage
            exit 1
            ;;
    esac
done

print_status "🚀 Setting up production system with HuggingFace embeddings..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "docker-compose.yml" ]]; then
    print_error "docker-compose.yml not found. Please run this script from the core directory."
    exit 1
fi

# Stop any running services
print_status "Stopping existing services..."
docker compose down 2>/dev/null || true

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p ./config
mkdir -p ./logs
mkdir -p ./watch_folder
mkdir -p ./processed
mkdir -p ./error

# Start services based on configuration
if [[ "$SKIP_OLLAMA" == "true" ]]; then
    print_status "Starting services without Ollama..."
    docker compose up -d processing-pipeline embedding-processor file-watcher
else
    print_status "Starting all services including Ollama..."
    docker compose up -d
fi

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Check service health
print_status "Checking service health..."

# Check embedding processor
if curl -s http://localhost:8007/health > /dev/null; then
    print_success "Embedding processor is healthy"
else
    print_warning "Embedding processor health check failed"
fi

# Check processing pipeline
if curl -s http://localhost:8003/health > /dev/null; then
    print_success "Processing pipeline is healthy"
else
    print_warning "Processing pipeline health check failed"
fi

# Check file watcher
if curl -s http://localhost:8009/health > /dev/null; then
    print_success "File watcher is healthy"
else
    print_warning "File watcher health check failed"
fi

# Initialize HuggingFace models if requested
if [[ "$INIT_MODELS" == "true" ]]; then
    print_status "Initializing HuggingFace models..."
    docker compose exec embedding-processor python init_huggingface.py
fi

# Run tests if requested
if [[ "$RUN_TESTS" == "true" ]]; then
    print_status "Running tests..."
    docker compose exec embedding-processor python test_embeddings.py
fi

# Show configuration summary
print_status "Configuration Summary:"
echo "  - Embedding Provider: HuggingFace (default)"
echo "  - Default Model: sentence-transformers/all-MiniLM-L6-v2"
echo "  - Cache Directory: /app/cache/huggingface"
echo "  - Device: CPU"
echo "  - Batch Size: 32"

# Show service URLs
print_status "Service URLs:"
echo "  - Embedding Processor: http://localhost:8007"
echo "  - Processing Pipeline: http://localhost:8003"
echo "  - File Watcher: http://localhost:8009"
echo "  - Core Processor: http://localhost:8001"

# Show usage instructions
print_status "Usage Instructions:"
echo ""
echo "1. Add files to the watch folder:"
echo "   cp your_document.pdf ./watch_folder/"
echo ""
echo "2. Check processing status:"
echo "   curl http://localhost:8009/api/v1/watch/status"
echo ""
echo "3. Test embedding generation:"
echo "   curl -X POST http://localhost:8007/embed \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"text\": \"Hello world\", \"provider\": \"huggingface\"}'"
echo ""
echo "4. Monitor logs:"
echo "   docker compose logs -f embedding-processor"
echo "   docker compose logs -f file-watcher"
echo ""

# Show health check commands
print_status "Health Check Commands:"
echo "  curl http://localhost:8007/health    # Embedding processor"
echo "  curl http://localhost:8003/health    # Processing pipeline"
echo "  curl http://localhost:8009/health    # File watcher"
echo "  curl http://localhost:8001/health    # Core processor"
echo ""

print_success "🎉 Production system setup completed with HuggingFace embeddings!"
print_success "The system is now configured to use HuggingFace as the default embedding provider."

if [[ "$SKIP_OLLAMA" == "true" ]]; then
    print_warning "Note: Ollama service was skipped. If you need Ollama later, run:"
    echo "  docker compose up -d ollama"
fi

print_status "Next steps:"
echo "1. Add files to ./watch_folder/ for automatic processing"
echo "2. Monitor processing with: docker compose logs -f"
echo "3. Check the dashboard at: http://localhost:8000"
echo "" 