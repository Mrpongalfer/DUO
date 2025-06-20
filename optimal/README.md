# Omnitide Nexus Microservice Initiator

## 🚀 Setup Wizard & Walkthrough

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+
- (Optional) Kubernetes & kubectl

### 2. Local Quickstart
#### a. Start MongoDB
```sh
docker-compose up -d
```
#### b. Build Omnitide Image
```sh
docker build -t omnitide .
```
#### c. Run Omnitide Service
```sh
docker run --rm -it -p 8080:8080 --env MONGO_URI=mongodb://host.docker.internal:27017 omnitide
```

### 3. Kubernetes Deployment
```sh
# Build and push image to your registry (edit as needed)
docker build -t <your-registry>/omnitide:latest .
docker push <your-registry>/omnitide:latest
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### 4. API Endpoints & Usage
#### a. Ingest Data
- **POST /ingest**
- Accepts any JSON. Example:
```sh
curl -X POST http://localhost:8080/ingest -H 'Content-Type: application/json' -d '{"user": {"id": 1, "name": "Alice"}, "event_time": "2025-06-19T12:00:00Z", "payload": {"score": 42}}'
```
#### b. Query Data
- **GET /query**
- **GET /query/{item_id}**
```sh
curl http://localhost:8080/query
curl http://localhost:8080/query/<item_id>
```
#### c. Live Patch Transformation Logic
- **POST /architects_patch/{patch_id}**
- Patch the transformation logic at runtime. Example:
```sh
curl -X POST http://localhost:8080/architects_patch/v2 -H 'Content-Type: application/json' -d '{"code": "async def custom_transform(data, transformed, meta):\n    if \"special\" in data:\n        transformed[\"special_handled\"] = True\n"}'
```
- All subsequent ingests will use the new logic immediately.

### 5. Swagger/OpenAPI Docs
- Visit [http://localhost:8080/docs](http://localhost:8080/docs) for interactive API documentation and live testing.

### 6. Logging & Monitoring
- All actions, errors, and self-healing events are logged with timestamps and levels (INFO, WARNING, ERROR, CRITICAL).
- Runtime performance is monitored and can trigger auto-patching (see `self_patch.py`).

### 7. How It Works
- **/ingest**: Accepts any JSON, infers schema, applies AI-driven and patchable transformation, persists to MongoDB.
- **/query**: Retrieves transformed data.
- **/architects_patch**: Allows you to evolve the transformation logic live, without restart.
- **Self-Healing**: If errors occur, the service retries, evolves, and logs all actions.
- **K8s**: Resource requests/limits and health probes ensure production resilience.

### 8. Verification
- POST to `/ingest` with sample JSON.
- GET `/query` to verify transformation and storage.
- POST to `/architects_patch/{patch_id}` to live-patch logic, then re-ingest and observe changes.
- Check `/docs` for live API testing.
- Observe logs for all actions and self-healing.

---
**Architect's Will is Absolute.**
