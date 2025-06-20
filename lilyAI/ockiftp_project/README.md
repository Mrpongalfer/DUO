# Omnitide Codex Knowledge Ingestion & Fine-Tuning Pipeline (OCKIFT-P)

This project provides a secure, production-ready FastAPI application for knowledge ingestion and Llama 3 fine-tuning orchestration. It is a core component of the Omnitide Nexus platform.

## Features
- `/ingest`: Securely upload training data (txt, jsonl)
- `/fine_tune`: Launch Llama 3 fine-tuning jobs on uploaded data
- HTTP Basic Auth for all endpoints
- Fine-tuning script for Llama 3 (HuggingFace Transformers)
- Dockerized for production
- Integrates with LCSAF and OMI for unified AI orchestration

## Usage

### Build & Run (Docker)
```sh
docker build -t ockiftp .
docker run -p 8000:8000 -e OCKIFT_USER=youruser -e OCKIFT_PASS=yourpass ockiftp
```

### API Endpoints
- `POST /ingest` (multipart file upload, requires HTTP Basic Auth)
- `POST /fine_tune` (JSON: {"file_id":..., "epochs":...}, requires HTTP Basic Auth)

### Fine-tuning Script
- Located at `fine_tuning_scripts/train.py`
- Uses Llama 3 (default: meta-llama/Meta-Llama-3-8B)

## Requirements
- Python 3.10+
- torch, transformers, fastapi, uvicorn

## Security
- All endpoints require HTTP Basic Auth
- Uploaded files and fine-tuned models are stored in `/tmp/ockiftp_uploads` and `/tmp/ockiftp_finetune` (can be changed)

## License
Proprietary / Architect's Absolute Genesis Edict
