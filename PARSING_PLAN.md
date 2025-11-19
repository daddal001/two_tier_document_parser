# Document Parsing Service - Implementation Plan

**Version:** 3.0 (Simplified Two-Service Architecture)
**Last Updated:** November 2025
**Status:** Implementation - Beta
**License Strategy:** Open-source parsing services (AGPL-3.0), proprietary application integration

---

## Executive Summary

This plan details the implementation of a **dual-parser architecture** for document processing, consisting of **two completely separate, independent microservices**:

1. **Fast Parser Service** - PyMuPDF4LLM for ultra-fast text extraction (0.12s/doc, no GPU, Python 3.13 no-GIL)
2. **Accurate Parser Service** - MinerU 2.6.4+ for high-quality extraction with images/tables/formulas (GPU-accelerated, scale-to-zero)

**Critical Architectural Separation:**
- ✅ **Two separate containers** - Different Dockerfiles, different base images (Python 3.13 vs vLLM/OpenAI)
- ✅ **Two different endpoints** - Fast: `http://fast-parser:8004/parse`, Accurate: `http://accurate-parser:8005/parse`
- ✅ **Different resource requirements** - Fast: 4 vCPUs/no GPU, Accurate: 2 vCPUs/1 GPU (T4)
- ✅ **Different scaling patterns** - Fast: Always-on HPA (2-10 pods), Accurate: Scale-to-zero HPA (0-5 pods)
- ✅ **Different namespaces** - Fast: `parsing-fast`, Accurate: `parsing-accurate`
- ✅ **Independent deployments** - Each service can be updated/scaled/restarted independently

**Key Design Principles:**
- **Simplicity**: Single `/parse` endpoint per service, synchronous request/response
- **No job management**: No queues, no job IDs, no polling - just parse and return
- **Stateless**: Zero data retention, ephemeral processing only
- **IP Protection**: Public repo contains ONLY Docker code, K8s/compliance stay private
- **Concurrency**: ThreadPoolExecutor + async FastAPI + GKE HPA for horizontal scaling
- **Python 3.13 no-GIL**: Fast parser achieves true thread parallelism (4 concurrent parses per pod)

---

## Architecture Overview

### Service Separation Strategy

**IMPORTANT:** These are **TWO COMPLETELY SEPARATE SERVICES** - different containers, different endpoints, different infrastructure.

| Aspect | Fast Parser Service | Accurate Parser Service |
|--------|---------------------|------------------------|
| **Container Image** | `gcr.io/PROJECT/fast-parser` | `gcr.io/PROJECT/accurate-parser` |
| **Base Image** | `python:3.13-slim` | `vllm/vllm-openai:v0.10.1.1` |
| **Dockerfile** | `fast/Dockerfile` | `accurate/Dockerfile` |
| **Endpoint** | `http://fast-parser.parsing-fast.svc.cluster.local:8004/parse` | `http://accurate-parser.parsing-accurate.svc.cluster.local:8005/parse` |
| **Parser** | PyMuPDF4LLM | MinerU 2.6.4+ |
| **Python Version** | 3.13 (no-GIL) | 3.10 (MinerU requirement) |
| **License** | AGPL-3.0 | AGPL-3.0 |
| **Speed** | 0.12s per document | 1.70-2.12 pages/second |
| **Output** | Markdown text only | Markdown + PNG images + tables + formulas |
| **API** | `POST /parse` → returns immediately | `POST /parse` → caller waits 1-3 min |
| **Job Management** | None (caller waits for response) | None (caller waits for response) |
| **Concurrency** | ThreadPoolExecutor (4 workers/pod) | ThreadPoolExecutor (2 workers/pod) |
| **GPU Required** | ❌ No | ✅ Yes (NVIDIA T4) |
| **CPU** | 4 vCPUs (4 threads w/ no-GIL) | 2 vCPUs (GPU bottleneck) |
| **Memory** | 2-4Gi | 16-32Gi |
| **Scaling Strategy** | Always-on, HPA 2-10 pods | Scale-to-zero, HPA 0-5 pods |
| **Cost/hour** | ~$0.05-0.10 | ~$0.35-0.50 (when running) |
| **Use Case** | Real-time text extraction | Batch processing for multimodal RAG |
| **Cold Start** | <10 seconds | ~30-60 seconds (GPU provisioning) |
| **Port** | 8004 | 8005 |
| **Namespace** | `parsing-fast` | `parsing-accurate` |
| **K8s Deployment** | `k8s/fast-parser/deployment.yaml` | `k8s/accurate-parser/deployment.yaml` |
| **Independent Updates** | ✅ Yes | ✅ Yes |

### Repository Strategy (IP Protection)

**Public Repository (`document-parsing-services`):**
- Contains: Docker code ONLY (app.py, parser.py, Dockerfile, requirements.txt)
- License: AGPL-3.0
- Purpose: Open-source parsing logic (reusable by community)
- Does NOT contain: K8s manifests, compliance docs, CI/CD, integration code

**Private Repository (`document_agent_v0.2`):**
- Contains: K8s manifests, compliance documentation, integration layer
- Integration: Git submodule pointer to public repo
- Deployment: Private K8s manifests deploy images built from public code
- IP Protection: Public repo has zero visibility into private infrastructure

**Why Git Submodule:**
- ⭐⭐⭐⭐⭐ **Best IP protection**: Complete separation of public/private code
- Public repo: Standalone, no references to private application
- Private repo: Points to specific commit of public repo
- Updates: `git submodule update` pulls latest parsing code
- Impossible to accidentally expose private code to public repo

---

## Deployment Architecture

**Two Independent Service Deployments:**

```
┌─────────────────────────────────────┐     ┌─────────────────────────────────────┐
│  Fast Parser Service                │     │  Accurate Parser Service            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │     │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                     │     │                                     │
│  Container: fast-parser             │     │  Container: accurate-parser         │
│  Image: gcr.io/PROJECT/fast-parser  │     │  Image: gcr.io/PROJECT/accurate     │
│  Base: python:3.13-slim             │     │  Base: nvidia/cuda:11.8.0           │
│  Port: 8004                         │     │  Port: 8005                         │
│  Namespace: parsing-fast            │     │  Namespace: parsing-accurate        │
│                                     │     │                                     │
│  Resources:                         │     │  Resources:                         │
│  ├─ CPU: 4 vCPUs                    │     │  ├─ CPU: 2 vCPUs                    │
│  ├─ Memory: 2-4Gi                   │     │  ├─ Memory: 16-32Gi                 │
│  └─ GPU: None ❌                     │     │  └─ GPU: 1x NVIDIA T4 ✅            │
│                                     │     │                                     │
│  Scaling:                           │     │  Scaling:                           │
│  ├─ HPA: 2-10 pods                  │     │  ├─ HPA: 0-5 pods                   │
│  ├─ Always-on (min 2)               │     │  ├─ Scale-to-zero (min 0)           │
│  └─ CPU threshold: 70%              │     │  └─ CPU threshold: 70%              │
│                                     │     │                                     │
│  Endpoint:                          │     │  Endpoint:                          │
│  POST /parse                        │     │  POST /parse                        │
│  └─ Returns in <1 second            │     │  └─ Returns in 1-3 minutes          │
│                                     │     │                                     │
└─────────────────────────────────────┘     └─────────────────────────────────────┘
           ▲                                            ▲
           │                                            │
           └────────────────────┬───────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │  Document Service     │
                    │  (backend-document)   │
                    │                       │
                    │  Calls appropriate    │
                    │  parser based on mode │
                    └───────────────────────┘
```

**Key Differences:**
1. **Different Docker builds** - Separate Dockerfiles, different base images
2. **Different endpoints** - Different DNS names, different ports
3. **Different resource allocation** - CPU-only vs GPU-required
4. **Different scaling behavior** - Always-on vs scale-to-zero
5. **Independent lifecycle** - Update/restart one without affecting the other

---

## Repository Structure

### Public Repository: `document-parsing-services` (AGPL-3.0)

**Minimal structure - Docker code ONLY:**

```
document-parsing-services/
├── README.md                      # Basic usage, API docs, Docker commands
├── LICENSE                        # AGPL-3.0 license text
├── fast/                          # Fast parser (PyMuPDF4LLM)
│   ├── app.py                     # FastAPI app (~50 lines)
│   ├── parser.py                  # Parser logic (~50 lines)
│   ├── models.py                  # Pydantic models (~30 lines)
│   ├── Dockerfile                 # Python 3.13-slim + PYTHON_GIL=0
│   └── requirements.txt           # pymupdf4llm, fastapi, uvicorn
└── accurate/                      # Accurate parser (MinerU)
    ├── app.py                     # FastAPI app (~60 lines)
    ├── parser.py                  # Parser logic (~100 lines)
    ├── models.py                  # Pydantic models (~40 lines)
    ├── Dockerfile                 # CUDA 11.8 + Python 3.10
    └── requirements.txt           # magic-pdf[full], fastapi, uvicorn
```

**Total: ~500 lines of code, 10 files**

**What's NOT in public repo:**
- ❌ Kubernetes manifests (private infrastructure)
- ❌ Compliance documentation (private)
- ❌ CI/CD workflows (private deployment)
- ❌ Integration code (private application logic)
- ❌ Monitoring configs (private)
- ❌ Network policies (private)
- ❌ Any reference to `document_agent_v0.2` or private services

---

### Private Repository: `document_agent_v0.2` (Proprietary)

**Integration structure:**

```
document_agent_v0.2/
├── parsing-services/              # Git submodule → public repo
│   ├── fast/                      # Points to public repo
│   └── accurate/                  # Points to public repo
├── k8s/
│   ├── fast-parser/               # Private K8s manifests
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── network-policy.yaml
│   └── accurate-parser/           # Private K8s manifests
│       ├── namespace.yaml
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── hpa.yaml
│       └── network-policy.yaml
├── backend-document/
│   └── services/
│       └── parsing_client.py      # Integration client
├── PARSING_PLAN.md                # This document (private)
├── COMPLIANCE_CHECK.md            # Whole system compliance (private)
└── [existing services...]
```

**Git submodule commands:**
```bash
# Add submodule
git submodule add https://github.com/YOUR_ORG/document-parsing-services.git parsing-services

# Update to latest
cd parsing-services && git pull origin main && cd ..
git add parsing-services && git commit -m "Update parsing services"

# Clone with submodules
git clone --recurse-submodules https://github.com/YOUR_ORG/document_agent_v0.2.git
```

---

## Service Implementation Details

### Fast Parser Service (PyMuPDF4LLM + Python 3.13 No-GIL)

**Technology Stack:**
- **Python 3.13** with `PYTHON_GIL=0` (free-threading enabled)
- FastAPI 0.115.0+
- pymupdf4llm 0.0.17+
- uvicorn[standard] 0.30.0+
- ThreadPoolExecutor (4 workers) - achieves true parallelism with no-GIL

**API Design:**

Single endpoint: `POST /parse`
- **Input**: PDF file via multipart/form-data
- **Output**: Markdown text (synchronous response)
- **Latency**: <1 second average
- **Concurrency**: 4 simultaneous requests per pod (no-GIL parallelism)
- **No job management**: Caller waits for response

```python
# POST /parse
# Request (multipart/form-data):
#   file: binary PDF data

# Response (200 OK):
{
  "markdown": "# Document Title\n\nContent...",
  "metadata": {
    "pages": 10,
    "processing_time_ms": 120,
    "parser": "pymupdf4llm",
    "version": "0.0.17"
  }
}

# GET /health
# Response: {"status": "healthy", "workers": 4, "no_gil": true}
```

**Implementation Summary (~150 lines total):**

**Key Architecture Decisions:**
1. **ThreadPoolExecutor (4 workers)** - Leverages Python 3.13 no-GIL for true parallelism
2. **Async FastAPI endpoint** - Allows multiple concurrent requests without blocking
3. **run_in_executor** - Offloads CPU-bound parsing to thread pool
4. **PyMuPDF4LLM** - Ultra-fast markdown extraction (0.12s average)

**Files:**
- `fast/app.py` - FastAPI app with ThreadPoolExecutor (~50 lines)
- `fast/parser.py` - PyMuPDF4LLM wrapper (~50 lines)
- `fast/models.py` - Pydantic response models (~30 lines)
- `fast/Dockerfile` - Python 3.13-slim with PYTHON_GIL=0
- `fast/requirements.txt` - fastapi, uvicorn, pymupdf4llm, httpx

**Dockerfile:**

```dockerfile
# fast/Dockerfile
FROM python:3.13-slim

# Enable free-threading (no-GIL mode)
ENV PYTHON_GIL=0

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8004/health')" || exit 1

# Run application (single worker - thread pool handles concurrency)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8004", "--workers", "1"]
```

**Why Python 3.13 + no-GIL:**
- **True thread parallelism**: 4 threads can run on 4 CPU cores simultaneously
- **Lower memory**: ThreadPoolExecutor uses ~10MB/worker vs ~50MB/process
- **Faster startup**: No process forking overhead
- **Simpler code**: No ProcessPoolExecutor, no IPC, no serialization
- **Compatibility**: PyMuPDF4LLM works with Python 3.13 (pure Python + C extensions are thread-safe)

**GKE Deployment (Private Repo):**

```yaml
# k8s/fast-parser/deployment.yaml (in private repo)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fast-parser
  namespace: parsing-fast
spec:
  replicas: 2  # Initial replicas, HPA will adjust
  selector:
    matchLabels:
      app: fast-parser
  template:
    metadata:
      labels:
        app: fast-parser
    spec:
      containers:
      - name: fast-parser
        image: gcr.io/YOUR_PROJECT/fast-parser:latest
        ports:
        - containerPort: 8004
        resources:
          requests:
            cpu: "4000m"      # 4 vCPUs for 4 workers (no-GIL)
            memory: "2Gi"
          limits:
            cpu: "4000m"
            memory: "4Gi"
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: PYTHON_GIL
          value: "0"          # Ensure no-GIL mode
        livenessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 5
          periodSeconds: 10
---
# k8s/fast-parser/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fast-parser-hpa
  namespace: parsing-fast
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fast-parser
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

### Accurate Parser Service (MinerU + GPU)

**Technology Stack:**
- **Python 3.10** (MinerU requirement)
- **vLLM/OpenAI** Base Image (`vllm/vllm-openai`)
- FastAPI 0.115.0+
- mineru[core] 2.6.4+
- uvicorn[standard] 0.30.0+
- ThreadPoolExecutor (2 workers) - GPU is bottleneck

**API Design:**

Single endpoint: `POST /parse`
- **Input**: PDF file via multipart/form-data
- **Output**: Markdown + images + tables + formulas (synchronous response)
- **Latency**: 1-3 minutes (caller waits)
- **Concurrency**: 2 simultaneous requests per pod (GPU queues internally)
- **No job management**: Caller waits for complete response

```python
# POST /parse
# Request (multipart/form-data):
#   file: binary PDF data

# Response (200 OK) - caller waits 1-3 minutes:
{
  "markdown": "# Document Title\n\n...",
  "images": [
    {
      "filename": "image_0.png",
      "base64": "iVBORw0KGgo...",
      "width": 800,
      "height": 600,
      "page": 1
    }
  ],
  "tables": [...],
  "formulas": [...],
  "metadata": {
    "pages": 20,
    "processing_time_ms": 95000,
    "parser": "mineru",
    "version": "2.5.0"
  }
}

# GET /health
# Response: {"status": "healthy", "workers": 2, "gpu_available": true}
```

**Implementation Summary (~250 lines total):**

**Key Architecture Decisions:**
1. **ThreadPoolExecutor (2 workers)** - GPU is bottleneck, 2 concurrent requests queue for GPU
2. **MinerU UNIPipe** - Automatic document classification and parsing
3. **Temporary file handling** - Ephemeral storage with immediate cleanup
4. **Image extraction** - PNG files with base64 encoding for transfer

**Files:**
- `accurate/app.py` - FastAPI app with ThreadPoolExecutor (~60 lines)
- `accurate/parser.py` - MinerU wrapper with image extraction (~100 lines)
- `accurate/models.py` - Pydantic response models (~40 lines)
- `accurate/Dockerfile` - CUDA 11.8 + Python 3.10
- `accurate/requirements.txt` - fastapi, uvicorn, magic-pdf[full], torch, Pillow

**Dockerfile:**

```dockerfile
# accurate/Dockerfile
FROM vllm/vllm-openai:v0.10.1.1

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
        fonts-noto-core \
        fonts-noto-cjk \
        fontconfig \
        libgl1 \
        python3-pip \
        git \
        wget \
        && \
    fc-cache -fv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
# Install python dependencies
RUN python3 -m pip install -r requirements.txt --break-system-packages

# Download MinerU models
RUN /bin/bash -c "mineru-models-download -s huggingface -m all"

# Copy application
COPY . .

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python3 -c "import httpx; httpx.get('http://localhost:8005/health')" || exit 1

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "1"]
```

**GKE Deployment (Scale-to-Zero):**

```yaml
# k8s/accurate-parser/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: accurate-parser
  namespace: parsing-accurate
spec:
  replicas: 0  # Start at zero, HPA will scale up on demand
  selector:
    matchLabels:
      app: accurate-parser
  template:
    metadata:
      labels:
        app: accurate-parser
    spec:
      nodeSelector:
        cloud.google.com/gke-accelerator: nvidia-tesla-t4
      containers:
      - name: accurate-parser
        image: gcr.io/YOUR_PROJECT/accurate-parser:latest
        ports:
        - containerPort: 8005
        resources:
          requests:
            cpu: "2000m"
            memory: "16Gi"
            nvidia.com/gpu: "1"
          limits:
            cpu: "4000m"
            memory: "32Gi"
            nvidia.com/gpu: "1"
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: CUDA_VISIBLE_DEVICES
          value: "0"
        livenessProbe:
          httpGet:
            path: /health
            port: 8005
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8005
          initialDelaySeconds: 30
          periodSeconds: 10
---
# k8s/accurate-parser/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: accurate-parser-hpa
  namespace: parsing-accurate
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: accurate-parser
  minReplicas: 0  # Scale to zero when idle
  maxReplicas: 5
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 minutes before scaling down
      policies:
      - type: Pods
        value: 1
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0  # Scale up immediately
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "10"
```

---

## Private Application Integration

### Document Service Client (Private Repo)

The `backend-document` service integrates with parsing services via simple HTTP requests. No job management needed - parsers return results synchronously.

**Integration Architecture:**
- **Service Discovery**: Kubernetes internal DNS (cross-namespace)
  - Fast parser: `http://fast-parser.parsing-fast.svc.cluster.local:8004`
  - Accurate parser: `http://accurate-parser.parsing-accurate.svc.cluster.local:8005`
- **HTTP Client**: httpx.AsyncClient with appropriate timeouts
- **Error Handling**: Automatic retry on transient failures, logging
- **Batch Processing**: asyncio.gather for concurrent requests

**ParsingServiceClient (~100 lines):**
- `parse_fast(pdf_bytes, filename)` - Returns in <1 second (timeout: 10s)
- `parse_accurate(pdf_bytes, filename)` - Returns in 1-3 minutes (timeout: 300s)
- `batch_parse_fast(files)` - Concurrent parsing of multiple PDFs

### Usage in Document Routes

**Document Upload Flow:**
1. User uploads PDF → FastAPI endpoint receives file
2. Choose parsing mode: `fast` (text-only, <1s) or `accurate` (images+tables, 1-3min)
3. Call appropriate parsing service (synchronous HTTP request)
4. Store markdown in MinIO (`documents/{user_id}/{document_name}/content.md`)
5. Store extracted images in MinIO (if accurate mode)
6. Return response with MinIO URLs

**Batch Processing Flow:**
1. User uploads multiple PDFs
2. FastAPI creates asyncio tasks for each file
3. `asyncio.gather` sends requests to fast parser concurrently
4. All 20 documents processed in ~3 seconds (across 10 pods × 4 workers)
5. Results aggregated and returned

**Key Endpoints:**
- `POST /documents/{user_id}/{document_name}/upload` - Single document upload
- `POST /documents/batch` - Batch document upload
- `GET /documents/{user_id}/{document_name}` - Retrieve parsed document from MinIO

---

## Network Security

### Kubernetes NetworkPolicy

```yaml
# k8s/fast-parser/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: fast-parser-ingress
  namespace: parsing-fast
spec:
  podSelector:
    matchLabels:
      app: fast-parser
  policyTypes:
  - Ingress
  ingress:
  # Allow from private document service only
  - from:
    - namespaceSelector:
        matchLabels:
          name: default  # Or your private app namespace
      podSelector:
        matchLabels:
          app: document  # backend-document service
    ports:
    - protocol: TCP
      port: 8004
  # Allow health checks from GKE control plane
  - from:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 8004
---
# k8s/accurate-parser/network-policy.yaml (same structure for port 8005)
```

---

## CI/CD Pipeline (Optional for Public Repo)

**GitHub Actions Workflow:**
- **Trigger**: Push to main, PR to main
- **Test Job**: Python 3.13 setup → Install deps → Run pytest → Upload coverage
- **Build-Push Job**: Build Docker image → Push to GCR with SHA and latest tags
- **Security**: Dependabot for dependency updates, Trivy for container scanning

**Separate workflows for fast and accurate parsers** (optional - user may prefer building from private repo)

---

## Testing Strategy

**Unit Tests:**
- Health endpoint verification
- Parse endpoint with valid PDF (verify markdown output, metadata)
- Parse endpoint with invalid input (error handling)
- Concurrency test (4 simultaneous requests for fast parser)

**Integration Tests:**
- Cross-namespace communication (Document Service → Parsing Services)
- Batch parsing (20 documents concurrently)
- Scale-to-zero verification (accurate parser)
- End-to-end flow (upload → parse → store in MinIO)

**Performance Tests:**
- Fast parser: 100 documents in <30 seconds
- Accurate parser: GPU utilization monitoring
- HPA scaling behavior under load

---

## Deployment Steps

### 1. Create Public Repository

```bash
# On GitHub
# Create new public repository: document-parsing-services
# License: AGPL-3.0
# Clone and initialize
git clone https://github.com/YOUR_ORG/document-parsing-services.git
cd document-parsing-services
# Copy fast-parser/ and accurate-parser/ code
# Copy k8s/ manifests
# Commit and push
```

### 2. Setup GKE Namespaces

```bash
# Create namespaces
kubectl create namespace parsing-fast
kubectl create namespace parsing-accurate

# Label namespaces for NetworkPolicy
kubectl label namespace parsing-fast name=parsing-fast
kubectl label namespace parsing-accurate name=parsing-accurate

# Apply network policies
kubectl apply -f k8s/fast-parser/network-policy.yaml
kubectl apply -f k8s/accurate-parser/network-policy.yaml
```

### 3. Build and Push Images

```bash
# Fast parser
cd fast-parser
docker build -t gcr.io/YOUR_PROJECT/fast-parser:latest .
docker push gcr.io/YOUR_PROJECT/fast-parser:latest

# Accurate parser
cd ../accurate-parser
docker build -t gcr.io/YOUR_PROJECT/accurate-parser:latest .
docker push gcr.io/YOUR_PROJECT/accurate-parser:latest
```

### 4. Deploy Services

```bash
# Deploy fast parser
kubectl apply -f k8s/fast-parser/deployment.yaml
kubectl apply -f k8s/fast-parser/service.yaml
kubectl apply -f k8s/fast-parser/hpa.yaml

# Deploy accurate parser
kubectl apply -f k8s/accurate-parser/deployment.yaml
kubectl apply -f k8s/accurate-parser/service.yaml
kubectl apply -f k8s/accurate-parser/hpa.yaml

# Verify deployments
kubectl get pods -n parsing-fast
kubectl get pods -n parsing-accurate
kubectl get hpa -n parsing-fast
kubectl get hpa -n parsing-accurate
```

### 5. Update Private Application

```bash
# In private repo (document_agent_v0.2)
# Update backend-document/services/parsing_client.py with ParsingServiceClient
# Update backend-document/routes/documents.py to use parsing_client
# Update backend-document/requirements.txt (no new dependencies needed, just httpx)

# Rebuild and redeploy document service
docker build -t gcr.io/YOUR_PROJECT/backend-document:latest ./backend-document
docker push gcr.io/YOUR_PROJECT/backend-document:latest
kubectl rollout restart deployment document -n default
```

---

## Monitoring & Observability

### Metrics to Track

**Fast Parser:**
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Success rate (%)
- Pod count (current replicas)
- CPU/Memory utilization

**Accurate Parser:**
- Job submission rate
- Job completion time (p50, p95, p99)
- GPU utilization (%)
- Scale-up/down events
- Pod spin-up time
- Cost per job

### Logging

**Structured JSON logging** with metadata only (no document content):
- Timestamp, level, service name
- Request ID, filename (not content)
- Processing time, pages count, parser version
- Error messages (sanitized, no sensitive data)
- Exported to Cloud Logging (90-day retention)

### Alerting Rules

**Critical Alerts:**
- Fast parser down (no healthy pods for 5 minutes)
- Accurate parser GPU unavailable (affects processing)
- High error rate (>10% errors over 10 minutes)

**Warning Alerts:**
- High latency (p95 >5x baseline)
- Scale-up failures (HPA unable to provision pods)
- Low disk space on MinIO

---

## Cost Optimization

### Estimated Monthly Costs (GKE Autopilot)

**Fast Parser (Always-On):**
- 2 replicas × 1 vCPU × 2GB RAM × 730 hours = ~$50-80/month
- Auto-scales to 10 replicas during peak: +$200-300/month peak hours

**Accurate Parser (Scale-to-Zero):**
- 0 replicas idle × 730 hours = $0/month idle
- 1 GPU pod (T4) × 2 vCPU × 16GB RAM × 100 hours/month = ~$80-120/month
- Usage-based: Only pay when processing batch jobs

**Total Estimated Cost:** $130-500/month depending on usage patterns

### Cost Reduction Strategies

1. **Preemptible/Spot Nodes for Accurate Parser** - 60-80% cost reduction
2. **Aggressive Scale-Down** - 5-minute stabilization window
3. **Batch Job Scheduling** - Process during off-peak hours
4. **Regional Selection** - Use cheapest GCP region with T4 GPUs
5. **Committed Use Discounts** - For predictable fast parser load

---

## Security Considerations

### AGPL-3.0 Compliance

**Requirements:**
1. **Source Code Disclosure**: Parsing services code must be publicly available (GitHub)
2. **Network Use Clause**: Users interacting over network must have access to source
3. **License Propagation**: Any modifications must also be AGPL-3.0

**Compliance Measures:**
- Public GitHub repository with full source code
- README with clear AGPL-3.0 license notice
- API responses include link to source repository:
  ```json
  {
    "metadata": {
      "source_code": "https://github.com/YOUR_ORG/document-parsing-services",
      "license": "AGPL-3.0"
    }
  }
  ```

### Data Security

**In-Transit:**
- TLS 1.3 for all external connections
- mTLS for internal GKE service-to-service communication (optional)

**At-Rest:**
- No persistent storage in parsing services (stateless)
- Temporary files deleted immediately after processing
- MinIO encryption handled by private application

**Access Control:**
- NetworkPolicy restricts access to private namespace only
- No public internet exposure
- Workload Identity for GCP resource access (if needed)

---

## Implementation Roadmap

### Week 1: Public Repo Creation
- [x] Create `document-parsing-services` repository (public, AGPL-3.0)
- [x] Implement fast parser (~150 lines: app.py, parser.py, models.py, Dockerfile, requirements.txt)
- [x] Implement accurate parser (~250 lines: app.py, parser.py, models.py, Dockerfile, requirements.txt)
- [x] Test Python 3.13 no-GIL locally (fast parser)
- [ ] Test concurrency (4 simultaneous requests to fast parser)
- [x] Write README with API docs and Docker usage

### Week 2: Private Repo Integration
- [ ] Add git submodule to `document_agent_v0.2`
- [ ] Create K8s manifests in private repo (k8s/fast-parser/, k8s/accurate-parser/)
- [ ] Build and push images to GCR
- [ ] Deploy to GKE Autopilot (namespaces, NetworkPolicy, HPA)
- [ ] Verify cross-namespace communication

### Week 3: Backend Integration
- [ ] Implement `ParsingServiceClient` in backend-document
- [ ] Update document routes to use parsing services
- [ ] Test E2E flow (upload → parse → store in MinIO)
- [ ] Test batch parsing (20 documents concurrently)
- [ ] Verify scale-to-zero for accurate parser

### Week 4: Production Readiness
- [ ] Setup monitoring (Prometheus/Grafana)
- [ ] Configure alerts (error rate, latency, GPU failures)
- [ ] Load testing (40 concurrent fast parses, 10 concurrent accurate)
- [ ] Expand COMPLIANCE_CHECK.md (whole system)
- [ ] Final documentation review

---

## Success Criteria

**Performance:**
- ✅ Fast parser: <1 second per document (target: 0.12s)
- ✅ Accurate parser: 1-3 minutes per document (GPU-accelerated)
- ✅ Concurrency: 4 simultaneous fast parses per pod (no-GIL)
- ✅ Batch processing: 40 documents in <10 seconds (10 pods × 4 workers)

**Availability:**
- ✅ Fast parser uptime: >99.9%
- ✅ Accurate parser scale-to-zero: 0 pods when idle >5 minutes
- ✅ Cold start: GPU pods spin up in <60 seconds

**Quality:**
- ✅ Image extraction: PNG files with correct dimensions
- ✅ Markdown accuracy: Preserves document structure
- ✅ No data loss: Ephemeral processing, secure cleanup

**Compliance & Security:**
- ✅ AGPL-3.0 compliance: Public repository with full source
- ✅ IP protection: Git submodule prevents code mixing
- ✅ Security: NetworkPolicy enforced, no public exposure
- ✅ Zero data retention: Immediate file cleanup

**Cost:**
- ✅ Fast parser: ~$150/month (2-10 pods, always-on)
- ✅ Accurate parser: ~$100/month (usage-based, scale-to-zero)
- ✅ Total: <$500/month for moderate usage (5000 fast + 500 accurate docs/month)

---

## Future Enhancements

1. **Table Extraction**: Dedicated CSV/JSON output for parsed tables
2. **Formula Recognition**: LaTeX output for mathematical formulas
3. **Multi-Language OCR**: Support for non-English documents (Arabic, Chinese, Japanese)
4. **Streaming Response**: Chunked markdown output for very large documents
5. **Format Support**: DOCX, PPTX, XLSX parsing
6. **OCR Improvements**: Custom OCR models for domain-specific documents
7. **Batch Optimization**: Priority queue for batch jobs (accurate parser)
8. **Metrics Export**: Prometheus metrics for parsing duration, error rates

---

## Concurrency Model

### Fast Parser (Python 3.13 No-GIL)

**Single Pod:**
```
Request 1 → Thread 1 (CPU core 1) → PyMuPDF4LLM → Response in 0.12s
Request 2 → Thread 2 (CPU core 2) → PyMuPDF4LLM → Response in 0.12s
Request 3 → Thread 3 (CPU core 3) → PyMuPDF4LLM → Response in 0.12s
Request 4 → Thread 4 (CPU core 4) → PyMuPDF4LLM → Response in 0.12s
Request 5 → Waits for Thread 1-4 to finish
```

**Multiple Pods (HPA 2-10):**
```
10 pods × 4 workers = 40 concurrent parses
100 requests → Distributed across pods → Complete in ~3 seconds
```

### Accurate Parser (GPU-Bound)

**Single Pod:**
```
Request 1 → Thread 1 → GPU queue → MinerU → Response in 90s
Request 2 → Thread 2 → GPU queue → MinerU → Response in 180s (waits for GPU)
Request 3 → Waits for Thread 1-2
```

**Multiple Pods (HPA 0-5, each with T4 GPU):**
```
5 pods × 1 GPU = 5 concurrent parses (GPU is bottleneck)
20 requests → 5 process immediately, 15 wait or trigger pod scale-up
```

**GKE Autopilot Scaling:**
- Fast parser: Scales based on CPU (70% threshold)
- Accurate parser: Scales based on CPU + custom metric (request queue)
- Scale-to-zero: Accurate parser pods terminate after 5 minutes idle

---

**End of Plan - Version 3.0**

**Next Steps:**
1. User creates public GitHub repository: `document-parsing-services`
2. User reviews and approves this plan
3. Begin Week 1: Implement fast and accurate parsers (~400 lines total)
4. Deploy to private GKE cluster with K8s manifests from private repo
