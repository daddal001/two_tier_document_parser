# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Version:** 1.0
**Last Updated:** November 2025
**Target AI Assistants:** Claude Code, Cursor AI, GitHub Copilot, and other development AI tools

> **Note:** This is the documentation file for the `two_tier_document_parser` repository (public open-source parsing services).

## Executive Summary

This repository implements **two completely independent microservices** for document parsing, designed for open-source distribution (AGPL-3.0) while protecting private infrastructure:

1. **Fast Parser Service** (`fast/`) - PyMuPDF4LLM for ultra-fast text extraction
   - Python 3.13 with no-GIL enabled (`PYTHON_GIL=0`) for true thread parallelism
   - CPU-only, 4 concurrent threads per pod
   - Performance: 0.12s per document, ~33 docs/second per pod
   - Port: 8004, Endpoint: `POST /parse`

2. **Accurate Parser Service** (`accurate/`) - MinerU 2.6.4+ for high-quality multimodal extraction
   - Python 3.10 (MinerU requirement)
   - GPU-accelerated (uses `vllm` on NVIDIA GPUs), scale-to-zero capable
   - Extracts markdown + PNG images + tables + formulas
   - Performance: 1.70-2.12 pages/second
   - Port: 8005, Endpoint: `POST /parse`

**Critical Architecture Principle**: These are TWO INDEPENDENT SERVICES with different Dockerfiles, base images, endpoints, and resource requirements. They are NOT modules in a monolithic application.

**IP Protection Strategy**: This public repository contains ONLY the parsing services code. Kubernetes manifests, compliance documentation, and integration code remain in the private `document_agent_v0.2` repository via git submodule.

## Repository Structure

```
two_tier_document_parser/
├── PARSING_PLAN.md            # Comprehensive implementation plan (planning phase)
├── CLAUDE.md                  # This documentation file
├── LICENSE                    # AGPL-3.0 license
├── README.md                  # Public-facing documentation
├── fast/                      # Fast parser service (~150 lines)
│   ├── app.py                 # FastAPI app with ThreadPoolExecutor (~50 lines)
│   ├── parser.py              # PyMuPDF4LLM wrapper (~50 lines)
│   ├── models.py              # Pydantic request/response models (~30 lines)
│   ├── Dockerfile             # python:3.13-slim base
│   └── requirements.txt       # pymupdf4llm, fastapi, uvicorn
├── accurate/                  # Accurate parser service (~250 lines)
│   ├── app.py                 # FastAPI app with ThreadPoolExecutor (~60 lines)
│   ├── parser.py              # MinerU wrapper with image extraction (~100 lines)
│   ├── models.py              # Pydantic request/response models (~40 lines)
│   ├── Dockerfile             # vllm/vllm-openai base
│   └── requirements.txt       # mineru[core], fastapi, uvicorn
└── tests/                     # Test suite (to be implemented)
    ├── fast/                  # Fast parser tests
    ├── accurate/              # Accurate parser tests
    └── integration/           # Integration tests
```

**Not in this repository** (kept in private `document_agent_v0.2` repo):
- Kubernetes manifests (`k8s/`)
- Compliance documentation
- CI/CD workflows
- Integration code
- Monitoring configurations
- Network policies

## MinerU Integration (Git Submodule)

This repository uses MinerU as a git submodule for the accurate parser service. The MinerU directory is a reference to the official [opendatalab/MinerU](https://github.com/opendatalab/MinerU) repository.

**Key Commands:**
```bash
# Clone repository with submodules
git clone --recurse-submodules <repo-url>

# If already cloned, initialize submodule
git submodule init
git submodule update

# Update MinerU to latest version
cd MinerU
git pull origin master
cd ..
git add MinerU
git commit -m "Update MinerU submodule"

# Check current MinerU version
git submodule status
```

**Installation for Development:**
```bash
# Install MinerU in editable mode
cd MinerU
pip install -e .[core]

# Download MinerU models (required for accurate parser)
mineru-models-download -s huggingface -m all

cd ..
```

**Why Git Submodules:**
- ✅ Pin to specific tested MinerU versions
- ✅ Easy updates to newer releases
- ✅ Clean separation between your code and MinerU
- ✅ Reduced repository size (reference, not full copy)
- ✅ Contribution-ready - can contribute improvements back to MinerU

**Documentation**: See [GIT_SUBMODULES.md](GIT_SUBMODULES.md) for complete submodule usage guide, troubleshooting, and best practices.

**Integration in Accurate Parser:**

The accurate parser service will import MinerU modules directly:

```python
# accurate/parser.py (to be implemented)
from magic_pdf.pipe.UNIPipe import UNIPipe
from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter
# ... additional MinerU imports
```

Since MinerU is installed in the Python environment via `pip install -e .[core]`, imports work seamlessly.

## Development Environment Setup

**Prerequisites:**
- Python 3.13 (for fast parser development)
- Python 3.10 (for accurate parser development)
- Docker Desktop (for containerized development)
- NVIDIA GPU with CUDA 11.8+ (for accurate parser local testing)
- Google Cloud SDK (for GCR image pushing)

**Quick Start:**
```bash
git clone <repo-url>
cd two_tier_document_parser

# Review implementation plan
cat PARSING_PLAN.md

# Start with fast parser (no GPU required)
cd fast/
pip install -r requirements.txt
PYTHON_GIL=0 uvicorn app:app --port 8004 --reload
```

## Common Development Commands

### Fast Parser Service

```bash
# Navigate to fast parser
cd fast/

# Install dependencies (requires Python 3.13)
pip install -r requirements.txt

# Run locally with no-GIL enabled
PYTHON_GIL=0 uvicorn app:app --host 0.0.0.0 --port 8004 --reload

# Test endpoint
curl -X POST http://localhost:8004/parse -F "file=@test.pdf"

# Health check
curl http://localhost:8004/health

# Build Docker image
docker build -t fast-parser:latest .

# Run container
docker run -p 8004:8004 -e PYTHON_GIL=0 fast-parser:latest

# Test concurrency (4 simultaneous requests)
for i in {1..4}; do
  curl -X POST http://localhost:8004/parse -F "file=@test.pdf" &
done
wait
```

### Accurate Parser Service

```bash
# Navigate to accurate parser
cd accurate/

# Install dependencies (requires Python 3.10)
pip install -r requirements.txt

# Download MinerU models (first time only)
mineru-models-download -s huggingface -m all

# Run locally
uvicorn app:app --host 0.0.0.0 --port 8005 --reload

# Test endpoint (takes 1-3 minutes)
curl -X POST http://localhost:8005/parse -F "file=@test.pdf"

# Health check
curl http://localhost:8005/health

# Build Docker image (requires CUDA base)
docker build -t accurate-parser:latest .

# Run container with GPU
docker run --gpus all -p 8005:8005 accurate-parser:latest
```

### Testing

```bash
# Run tests for fast parser
cd fast/ && pytest

# Run tests for accurate parser
cd accurate/ && pytest

# Integration tests (requires both services running)
pytest tests/integration/
```

### Docker Build & Push

```bash
# Fast parser
cd fast/
docker build -t gcr.io/YOUR_PROJECT/fast-parser:latest .
docker push gcr.io/YOUR_PROJECT/fast-parser:latest

# Accurate parser
cd accurate/
docker build -t gcr.io/YOUR_PROJECT/accurate-parser:latest .
docker push gcr.io/YOUR_PROJECT/accurate-parser:latest
```

## Key Architecture Details

### Python 3.13 No-GIL (Fast Parser Only)

The fast parser uses Python 3.13's experimental no-GIL mode for true thread parallelism:

- **Enable no-GIL**: Set `PYTHON_GIL=0` environment variable
- **Concurrency**: ThreadPoolExecutor with 4 workers achieves 4x parallelism on 4 CPU cores
- **Resource Allocation**: Request 4 vCPUs to match thread count
- **Performance**: 4 concurrent parses at 0.12s each = ~33 docs/second per pod

**Critical**: The accurate parser uses Python 3.10 (MinerU requirement) and does NOT use no-GIL.

### API Design Pattern

Both services use the **same synchronous request/response pattern**:

```python
# Request
POST /parse
Content-Type: multipart/form-data
Body: file=<binary PDF>

# Response (synchronous - caller waits)
{
  "markdown": "# Content...",
  "metadata": {
    "pages": 10,
    "processing_time_ms": 120,
    "parser": "pymupdf4llm|mineru",
    "version": "x.x.x"
  },
  "images": [...],  # Only for accurate parser
  "tables": [...],  # Only for accurate parser
  "formulas": [...]  # Only for accurate parser
}
```

**No job management** - No job IDs, no polling, no queues. Just synchronous parse and return.

### Concurrency Model

**Fast Parser (CPU-bound)**:
- ThreadPoolExecutor with 4 workers
- Each request runs in separate thread
- Python 3.13 no-GIL enables true parallelism
- 4 concurrent parses per pod (no blocking)

**Accurate Parser (GPU-bound)**:
- ThreadPoolExecutor with 2 workers
- GPU is bottleneck, requests queue for GPU access
- Multiple pods scale horizontally (1 GPU per pod)
- Scale-to-zero when idle >5 minutes

### Stateless & Ephemeral

Both services are **completely stateless**:
- No database connections
- No persistent storage
- Temporary files deleted immediately after processing
- Zero data retention
- No logging of document content (metadata only)

### License & IP Protection

- **License**: AGPL-3.0 (copyleft open-source)
- **Public Repository**: Contains ONLY Docker code (app.py, parser.py, Dockerfile)
- **Private Repository**: Contains K8s manifests, compliance docs, integration code
- **Strategy**: Git submodule separates public parsing code from private infrastructure

**Compliance Requirement**: API responses must include source code link:
```json
{
  "metadata": {
    "source_code": "https://github.com/YOUR_ORG/document-parsing-services",
    "license": "AGPL-3.0"
  }
}
```

## Implementation Guidelines

### Code Size Targets

Keep implementations minimal and focused:
- Fast parser: ~150 lines total (app.py ~50, parser.py ~50, models.py ~30)
- Accurate parser: ~250 lines total (app.py ~60, parser.py ~100, models.py ~40)

### Error Handling

- Return 400 for invalid input (non-PDF, corrupted file)
- Return 500 for parsing failures
- Log errors with request ID, filename (NEVER log document content)
- Sanitize error messages (no file paths, no sensitive data)

### Security Considerations

- NetworkPolicy restricts access to private namespaces only
- No public internet exposure
- TLS 1.3 for external connections
- Temporary files with secure cleanup (`tempfile` module)
- No secrets in code or environment variables

### Resource Allocation

**Fast Parser**:
- CPU: 4 vCPUs (matches ThreadPoolExecutor workers)
- Memory: 2-4Gi
- GPU: None
- Scaling: HPA 2-10 pods, always-on

**Accurate Parser**:
- CPU: 2 vCPUs
- Memory: 16-32Gi
- GPU: 1x NVIDIA T4
- Scaling: HPA 0-5 pods, scale-to-zero

## Deployment Architecture

**IMPORTANT**: These services are deployed to **separate namespaces** in GKE:
- Fast parser: `parsing-fast` namespace
- Accurate parser: `parsing-accurate` namespace

Kubernetes manifests are in the **private repository** (`document_agent_v0.2/k8s/`), NOT in this public repo.

Service DNS (internal only):
- `http://fast-parser.parsing-fast.svc.cluster.local:8004`
- `http://accurate-parser.parsing-accurate.svc.cluster.local:8005`

## Performance Targets

**Fast Parser**:
- Latency: <1 second per document (target: 0.12s)
- Throughput: 40 concurrent parses (10 pods × 4 workers)
- Batch: 100 documents in <30 seconds

**Accurate Parser**:
- Latency: 1-3 minutes per document (GPU processing)
- Throughput: 1.70-2.12 pages/second
- Cold start: <60 seconds (GPU provisioning)

## Integration with Private Application

The private `backend-document` service calls these parsing services via HTTP:

```python
# Fast parsing (text-only)
async with httpx.AsyncClient(timeout=10.0) as client:
    response = await client.post(
        "http://fast-parser.parsing-fast.svc.cluster.local:8004/parse",
        files={"file": pdf_bytes}
    )

# Accurate parsing (images+tables)
async with httpx.AsyncClient(timeout=300.0) as client:
    response = await client.post(
        "http://accurate-parser.parsing-accurate.svc.cluster.local:8005/parse",
        files={"file": pdf_bytes}
    )
```

Note different timeout values (10s vs 300s).

## Common Development Patterns

### Adding New Parser Features

1. Update `parser.py` with new extraction logic
2. Update `models.py` with new response fields
3. Update `app.py` if endpoint behavior changes
4. Add tests for new functionality
5. Update API documentation in README
6. Rebuild Docker image and redeploy

### Debugging Parsing Issues

1. Check health endpoint: `GET /health`
2. Review structured logs (no document content, only metadata)
3. Test locally with problematic PDF
4. Verify Python version (3.13 for fast, 3.10 for accurate)
5. Check GPU availability (accurate parser only): `nvidia-smi`

### Performance Optimization

**Fast Parser**:
- Ensure `PYTHON_GIL=0` is set
- Verify 4 vCPUs are allocated
- Monitor CPU utilization (should hit 400% under load)
- Adjust HPA thresholds based on latency

**Accurate Parser**:
- Monitor GPU utilization (should be >80% during parsing)
- Profile MinerU pipeline stages
- Optimize image extraction (PNG compression)
- Adjust scale-to-zero stabilization window

## Monitoring & Observability

### Key Metrics

Both services expose `/health` endpoint with:
```json
{
  "status": "healthy",
  "workers": 4,  // or 2 for accurate parser
  "no_gil": true,  // fast parser only
  "gpu_available": true  // accurate parser only
}
```

### Structured Logging

Log format (JSON):
```json
{
  "timestamp": "2025-11-17T10:30:00Z",
  "level": "INFO",
  "service": "fast-parser",
  "request_id": "uuid",
  "filename": "document.pdf",  // filename only, NOT content
  "pages": 10,
  "processing_time_ms": 120,
  "parser_version": "0.0.17"
}
```

**NEVER log document content or sensitive metadata.**

## Environment Configuration

**No secrets in this repository** - All configuration is runtime-based:

**Fast Parser Environment Variables:**
- `LOG_LEVEL` - Logging level (default: INFO)
- `PYTHON_GIL` - Must be set to `0` for no-GIL mode
- `WORKERS` - ThreadPoolExecutor workers (default: 4)

**Accurate Parser Environment Variables:**
- `LOG_LEVEL` - Logging level (default: INFO)
- `CUDA_VISIBLE_DEVICES` - GPU device ID (default: 0)
- `WORKERS` - ThreadPoolExecutor workers (default: 2)

**GCR Image Naming:**
- Fast parser: `gcr.io/YOUR_PROJECT/fast-parser:latest`
- Accurate parser: `gcr.io/YOUR_PROJECT/accurate-parser:latest`

Replace `YOUR_PROJECT` with your actual GCP project ID when building/pushing images.

## Testing & Quality Assurance

**Unit Testing Strategy:**
```bash
# Fast parser tests
cd fast/
pytest tests/ -v

# Accurate parser tests
cd accurate/
pytest tests/ -v
```

**Test Coverage Requirements:**
- Health endpoint verification
- Parse endpoint with valid PDF (verify structure, metadata)
- Parse endpoint with invalid input (error handling)
- Concurrency test (multiple simultaneous requests)
- Memory leak detection (process same PDF 1000x)

**Integration Testing:**
```bash
# Start both services
docker compose up --build

# Run integration tests
pytest tests/integration/ -v
```

**Performance Benchmarks:**
- Fast parser: 100 documents in <30 seconds
- Accurate parser: GPU utilization >80% during processing
- Memory usage: Fast <4Gi, Accurate <32Gi

**Code Quality Standards:**
- Type hints on all functions
- Docstrings for public APIs
- FastAPI automatic OpenAPI docs (`/docs` endpoint)
- Structured JSON logging (no print statements)
- Error handling with specific HTTP status codes

## Common Issues

**Fast Parser Issues:**

**Issue**: "ImportError: No module named pymupdf4llm"
- **Solution**: Ensure Python 3.13 is active: `python --version`, then `pip install -r requirements.txt`

**Issue**: "GIL not disabled, threading not parallel"
- **Solution**: Verify `PYTHON_GIL=0` environment variable is set: `echo $PYTHON_GIL`

**Issue**: "Low CPU utilization (<400%) under load"
- **Solution**: Check thread count matches vCPUs, verify no-GIL mode active, profile with `py-spy`

**Accurate Parser Issues:**

**Issue**: "CUDA not available" or "No GPU detected"
- **Solution**: Check NVIDIA drivers: `nvidia-smi`, verify Docker has GPU access: `docker run --gpus all nvidia/cuda:11.8.0-base nvidia-smi`

**Issue**: "Out of memory (OOM) during parsing"
- **Solution**: Reduce batch size, increase memory limit to 32Gi, check for memory leaks with `memory_profiler`

**Issue**: "MinerU models not found"
- **Solution**: Models should download at Docker build time. Manually download: `mineru-models-download -s huggingface -m all`

**General Issues:**

**Issue**: "Port already in use (8004 or 8005)"
- **Solution**: Check running processes: `lsof -i :8004`, kill or change port in command

**Issue**: "Docker build fails with 'no space left on device'"
- **Solution**: Clean Docker: `docker system prune -a --volumes`

**Issue**: "AGPL-3.0 compliance - what to include in responses?"
- **Solution**: API metadata must include source code link (see License & IP Protection section)

## AI Assistant Behavioral Guidelines

**Core Principles:**
1. **ALWAYS edit existing files** over creating new ones. This repository is minimal by design (~500 lines total).
2. **Respect the two-service architecture** - NEVER merge fast and accurate parsers into a single service.
3. **Follow existing patterns** - FastAPI with ThreadPoolExecutor, Pydantic models, structured logging.
4. **Maintain AGPL-3.0 compliance** - Source code must remain public, include license headers.
5. **Keep code minimal** - Target: Fast parser ~150 lines, Accurate parser ~250 lines.

**Technology Guidelines:**

**Python/FastAPI:**
- Use async FastAPI endpoints with `run_in_executor` for CPU-bound tasks
- ThreadPoolExecutor for concurrency (NOT ProcessPoolExecutor)
- Type hints on all functions (`def parse_pdf(file: UploadFile) -> ParseResponse:`)
- Pydantic models for request/response validation
- Structured logging with JSON format (no print statements)
- Error handling with specific HTTP status codes (400, 413, 500, 503)

**Docker:**
- Multi-stage builds (builder + runner stages)
- Minimal base images (python:3.13-slim for fast, nvidia/cuda for accurate)
- Health checks in Dockerfile (`HEALTHCHECK` instruction)
- No secrets in images (use environment variables at runtime)
- Layer caching optimization (COPY requirements first, then code)

**Testing:**
- pytest with fixtures for FastAPI TestClient
- Parametrized tests for different PDF types
- Mock external dependencies (if any added later)
- Performance benchmarks in CI/CD

**Security:**
- Temporary file cleanup (`tempfile` module with context managers)
- Input validation (file size limits, MIME type checking)
- No logging of document content (only metadata: filename, pages, processing time)
- Sanitized error messages (no file paths, no sensitive data)

**Critical Files (Modify with Caution):**
- `fast/Dockerfile` - Python 3.13 no-GIL configuration is critical
- `accurate/Dockerfile` - CUDA/cuDNN versions must match MinerU requirements
- `*/parser.py` - Core parsing logic, test thoroughly after changes
- `PARSING_PLAN.md` - Master implementation plan, update only when architecture changes

**Primary Development Areas:**
- `fast/app.py`, `fast/parser.py`, `fast/models.py`
- `accurate/app.py`, `accurate/parser.py`, `accurate/models.py`
- `tests/` - Test coverage for all endpoints

**Protected Files:**
- `LICENSE` - AGPL-3.0, do not modify
- `CLAUDE.md` - This file, update only when architecture/patterns change

**Code Review Checklist:**
Before marking implementation complete, verify:
- [ ] Type hints on all functions
- [ ] Health endpoint returns correct structure
- [ ] Parse endpoint validates input (file size, MIME type)
- [ ] Error handling returns appropriate HTTP status codes
- [ ] Logging is structured JSON (no print statements)
- [ ] Temporary files cleaned up (no leaks)
- [ ] AGPL-3.0 compliance (source code link in metadata)
- [ ] Docker builds successfully (both services)
- [ ] Tests pass (unit + integration)
- [ ] Documentation updated (README, API docs)

## Development Workflow

**Implementing New Features:**
1. Review PARSING_PLAN.md for alignment with architecture
2. Create feature branch: `git checkout -b feature/name`
3. Update relevant `parser.py` with new extraction logic
4. Update `models.py` with new response fields (if applicable)
5. Update `app.py` if endpoint behavior changes
6. Add tests in `tests/` directory
7. Update API documentation in README
8. Test locally: `pytest` and manual endpoint testing
9. Build Docker image: `docker build -t parser:test .`
10. Run integration tests with Docker container
11. Create pull request with description

**Debugging Workflow:**
1. Check health endpoint: `curl http://localhost:800X/health`
2. Review logs (structured JSON output)
3. Test with problematic PDF locally
4. Use FastAPI interactive docs: `http://localhost:800X/docs`
5. Profile performance: `py-spy record --native -- python app.py`
6. Check GPU usage (accurate parser): `nvidia-smi -l 1`
7. Memory profiling: `mprof run app.py` (accurate parser)

**Release Workflow:**
1. Update version in metadata response
2. Tag release: `git tag -a v1.0.0 -m "Release 1.0.0"`
3. Build production images: `docker build -t gcr.io/PROJECT/parser:v1.0.0 .`
4. Push to GCR: `docker push gcr.io/PROJECT/parser:v1.0.0`
5. Update private repository to use new image tag
6. Deploy to GKE (from private repository)
7. Monitor metrics for regressions

## Cross-Session Continuity

**CLAUDE_PLAN.md Protocol:**

When implementing features from PARSING_PLAN.md, maintain `CLAUDE_PLAN.md` for tracking progress across sessions.

**Purpose:**
- Persistent visibility into current implementation status
- Track which components are completed vs pending
- Document deviations from original plan
- Enable seamless AI assistant handoff between sessions

**Rules:**
1. **Starting new implementation:** Create/clear `CLAUDE_PLAN.md`, extract relevant section from PARSING_PLAN.md
2. **Progress updates:** Mark tasks as ✅ done, ⏳ in progress, or ❌ blocked
3. **Deviations:** Document any changes from original plan with rationale
4. **Completion:** Add "COMPLETED" status, keep file until next implementation starts

**Structure:**
```markdown
# Implementation: [Feature Name]
**Date Started:** YYYY-MM-DD
**Status:** In Progress | Completed | Blocked
**Plan Source:** PARSING_PLAN.md Week X

## Tasks
- [✅] Task 1
- [⏳] Task 2 (in progress)
- [ ] Task 3 (pending)

## Deviations
- Changed X to Y because Z

## Notes
- Key decisions made
- Blockers encountered
```

**Example Usage:**
```markdown
# Implementation: Fast Parser Service
**Date Started:** 2025-11-17
**Status:** In Progress
**Plan Source:** PARSING_PLAN.md Week 1

## Tasks
- [✅] Created fast/app.py with FastAPI application
- [✅] Implemented fast/parser.py with PyMuPDF4LLM wrapper
- [⏳] Writing fast/models.py Pydantic models
- [ ] Creating Dockerfile with Python 3.13 no-GIL
- [ ] Adding tests

## Notes
- Used ThreadPoolExecutor(4) for concurrency (matches plan)
- PYTHON_GIL=0 critical for performance
```

---

**Document Version:** 1.0
**Last Updated:** November 2025
**Maintainer:** AI Assistant Teams (Claude Code, Cursor AI, GitHub Copilot, etc.)
**Authority:** Primary documentation for AI assistant interactions with this codebase

**Status:** Planning Phase - No code implemented yet. See PARSING_PLAN.md for full implementation roadmap.

**Related Documentation:**
- `PARSING_PLAN.md` - Comprehensive implementation plan (Week 1-4 roadmap)
- `README.md` - Public-facing documentation (API usage, Docker instructions)
- `LICENSE` - AGPL-3.0 license text
