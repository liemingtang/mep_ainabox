#!/usr/bin/env bash
set -euo pipefail

log() { echo "[entrypoint][$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

# Defaults
: "${EMBEDDING_PROVIDER:=huggingface}"
: "${HF_DEFAULT_MODEL:=sentence-transformers/all-MiniLM-L6-v2}"
: "${HF_CACHE_DIR:=/app/cache/huggingface}"
: "${HF_DEVICE:=cpu}"
: "${HF_BATCH_SIZE:=32}"
: "${QDRANT_HOST:=qdrant}"
: "${QDRANT_PORT:=6333}"
: "${QDRANT_API_KEY:=}"
: "${QDRANT_COLLECTION:=documents}"
: "${RUN_INIT_HF:=true}"
: "${RUN_INIT_QDRANT:=true}"

log "Starting Embedding Processor (HF) entrypoint"
log "Provider=$EMBEDDING_PROVIDER model=$HF_DEFAULT_MODEL cache=$HF_CACHE_DIR device=$HF_DEVICE"

# Optional: Pre-warm / download model
if [[ "${RUN_INIT_HF}" == "true" ]]; then
  log "Running HuggingFace initialization"
  python3 /app/init_huggingface.py || log "HF init completed with warnings"
else
  log "Skipping HF initialization (RUN_INIT_HF=$RUN_INIT_HF)"
fi

# Wait for Qdrant to be up (best-effort)
if [[ "${RUN_INIT_QDRANT}" == "true" ]]; then
  log "Waiting for Qdrant at ${QDRANT_HOST}:${QDRANT_PORT}"
  for i in {1..20}; do
    if python3 - <<PY
import sys, httpx, os
host=os.getenv('QDRANT_HOST','qdrant'); port=os.getenv('QDRANT_PORT','6333')
try:
    r=httpx.get(f"http://{host}:{port}/collections", timeout=2.0)
    ok = r.status_code==200
except Exception:
    ok=False
sys.exit(0 if ok else 1)
PY
    then
      log "Qdrant is reachable"
      break
    fi
    sleep 2
  done

  # Ensure collection exists (best-effort)
  log "Ensuring Qdrant collection '${QDRANT_COLLECTION}' exists"
  python3 - <<PY || true
import os, httpx, json
host=os.getenv('QDRANT_HOST','qdrant'); port=os.getenv('QDRANT_PORT','6333')
api=os.getenv('QDRANT_API_KEY',''); col=os.getenv('QDRANT_COLLECTION','documents')
headers={'api-key': api} if api else {}
base=f"http://{host}:{port}"
try:
    r=httpx.get(f"{base}/collections/{col}", headers=headers, timeout=5.0)
    if r.status_code==200:
        print("collection exists")
    else:
        # default vector size; service will upsert actual later
        payload={"vectors": {"size": 768, "distance": "Cosine"}}
        rc=httpx.put(f"{base}/collections/{col}", headers={**headers, 'Content-Type':'application/json'}, json=payload, timeout=10.0)
        rc.raise_for_status()
        print("collection created")
except Exception as e:
    print(f"qdrant ensure collection warning: {e}")
PY
else
  log "Skipping Qdrant init (RUN_INIT_QDRANT=$RUN_INIT_QDRANT)"
fi

# If arguments provided, run them; otherwise start API server
if [[ "$#" -gt 0 ]]; then
  log "Executing custom command: $*"
  exec "$@"
else
  log "Starting API: python3 main.py"
  exec python3 /app/main.py
fi


