# Batch Processing System

## Overview

The batch processing system pulls pending work from the `file_processing_queue` table, finds the corresponding files on disk, extracts text, stores metadata and content in Elasticsearch, and (optionally) generates embeddings to store in Qdrant. It supports running as a local orchestrator that launches a containerized worker with dynamic folder mounts, or by running the worker directly inside a Docker container.

## Architecture

### Components

1. `batch_process_file_queue.py` (orchestrator)
   - Connects to PostgreSQL and queries pending items
   - Groups items by `parent_directory` for efficient, per-folder mounts
   - Launches a worker container with dynamic mounts and passes environment for embeddings/Qdrant
   - Can also run the worker directly if already inside Docker

2. `process_file_processing_queue.py` (worker)
   - Loads items from a JSON file (when started by the orchestrator) or queries DB directly
   - Resolves each file path using `MOUNT_POINTS` and known mount locations
   - Extracts text (fast local extraction for common types, Docker fallback for others)
   - Indexes metadata and content into Elasticsearch (`documents` and `document_content` indices)
   - Optionally generates embeddings (HuggingFace service or Ollama) and stores them in Qdrant
   - Updates item status: `processing` → `completed` or `failed`, with retry accounting
   - Provides verification and statistics helpers (`--verify-only`, `--stats-only`)

3. `batch_process_file_queue.sh` (container wrapper)
   - Builds the worker image if missing
   - Runs the worker inside Docker with the config directory mounted
   - Forwards arguments to the worker; additional flags can be passed via `--script-args`

4. Docker assets
   - `Dockerfile`, `build_docker.sh`, `requirements.txt`
   - Image contains both the worker and processors (text, embedding)

## Database Schema

Key fields used from `file_processing_queue` (joined with `file_info`):

- `id`, `file_info_id`, `file_path`, `filename`, `priority`, `processor_type`, `status`, `error_message`, `retry_count`, `max_retries`
- From `file_info`: `parent_directory`, `file_size`, `file_type`, `mime_type`, `checksum`, `created_time`, `modified_time`

## Usage

### Option A: Run the orchestrator (launches a worker container)

```bash
cd mep_ainabox/core/batch
python3 batch_process_file_queue.py --limit 10

# Filter by processor
python3 batch_process_file_queue.py --processor-type text_processor --limit 5

# Dry run (no status updates)
python3 batch_process_file_queue.py --dry-run --limit 5

# Pass-through flags to the worker
python3 batch_process_file_queue.py --limit 5 \
  --script-args --continuous --interval 60 --no-verify
```

### Option B: Run the worker directly in Docker (wrapper)

```bash
cd mep_ainabox/core/batch
./build_docker.sh  # one-time build (image: mep-folder-scanner:latest)

# Process a batch
./batch_process_file_queue.sh --limit 10

# Filter by processor type
./batch_process_file_queue.sh --processor-type text_processor

# Continuous worker loop (every 60s)
./batch_process_file_queue.sh --script-args --continuous --interval 60

# Verification/stats modes
./batch_process_file_queue.sh --verify-only
./batch_process_file_queue.sh --stats-only

# Dry run preview
./batch_process_file_queue.sh --dry-run --limit 5
```

Worker flags that are supported (pass directly, or via `--script-args` from the orchestrator):

- `--processor-type <type>`
- `--limit <number>`
- `--dry-run`
- `--continuous`
- `--interval <seconds>`
- `--no-verify` | `--verify-only`
- `--no-stats`  | `--stats-only`
- `--debug-paths`

## How It Works

### 1) Query pending items

```sql
SELECT q.id, q.file_info_id, q.file_path, q.filename, q.priority,
       q.processor_type, q.metadata, q.retry_count, q.max_retries,
       f.parent_directory, f.file_size, f.file_type, f.mime_type,
       f.checksum, f.created_time, f.modified_time
FROM file_processing_queue q
JOIN file_info f ON q.file_info_id = f.id
WHERE q.status = 'pending'
ORDER BY q.priority DESC, q.created_at ASC
LIMIT ?
```

### 2) Group by folder and mount dynamically

The orchestrator mounts each unique `parent_directory` into the worker container under `/mnt/<folder>` and exports a comma-separated `MOUNT_POINTS` env var for the worker to search.

### 3) Process files

- Fast local extraction for text-like formats; Docker text processor fallback for others
- Index document metadata and content into Elasticsearch
- Optionally call embedding service and store vectors in Qdrant
- Update queue status and track retries

## Docker Image

- Image: `mep-folder-scanner:latest` (built by `./build_docker.sh`)
- Includes Python 3.11, Docker CLI, worker + processors
- Default entrypoint is `python3`

Environment passed through to the worker (defaults shown):

- `EMBEDDING_PROVIDER=huggingface`
- `EMBEDDING_PROCESSOR_URL=http://localhost:8007/process`
- `OLLAMA_HOST=localhost`, `OLLAMA_PORT=11434`, `OLLAMA_DEFAULT_MODEL=nomic-embed-text`
- `QDRANT_HOST=localhost`, `QDRANT_PORT=6333`, `QDRANT_COLLECTION=documents`, `QDRANT_API_KEY` (optional)

Notes:
- When the worker runs inside Docker, it executes processors directly (no nested Docker required)
- Host networking (`--network host`) is used so service URLs can use `localhost`

## Elasticsearch Integration

- Metadata index: `documents` (one document per file)
- Content index: `document_content` (stores extracted text and stats)
- Verification helpers check presence of metadata/content and aggregate stats

## Error Handling and Retries

- Missing file → item marked `failed` with error message
- Processor failure → item marked `failed` and error recorded
- `retry_count` is incremented on failure up to `max_retries`

## Status Values (queue items)

- `pending` → `processing` → `completed` | `failed`

## Examples

```bash
# Process all pending items (batch of 100)
./batch_process_file_queue.sh --limit 100

# Only process .txt items (after queueing)
./queue_file_processing.sh --file-type .txt --processor-type text_processor
./batch_process_file_queue.sh --processor-type text_processor

# Verify Elasticsearch only (no processing)
./batch_process_file_queue.sh --verify-only --limit 5
```

## Troubleshooting

- Docker not running: start the Docker daemon
- Permission denied: ensure your user can run Docker
- File not found: check `parent_directory` and mounts
- Database connection failed: verify `core/config/main.yaml`

Logs:

```bash
# Worker logs
docker logs <container_name>

# Quick DB peek
docker exec -it mep-postgres psql -U mep_user -d mep_ainabox -c \
  "SELECT filename, status, created_at, completed_at FROM file_processing_queue ORDER BY created_at DESC LIMIT 10;"
```

## Related Docs

- `DOCKER_USAGE.md` — building and running the scanner image
- `FOLDER_SCANNER_QUICK_REFERENCE.md` — folder scanning/queueing
- `CONCURRENT_SCAN_PROCESSING.md` — concurrent shared-volume mounting strategy