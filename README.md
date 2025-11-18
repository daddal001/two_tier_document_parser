# Two-Tier Document Parser

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](LICENSE)
[![Status: Planning Phase](https://img.shields.io/badge/Status-Planning%20Phase-yellow.svg)](PARSING_PLAN.md)

**High-performance, open-source PDF parsing microservices with dual parsing strategies: ultra-fast text extraction and GPU-accelerated multimodal parsing.**

---

## Overview

This repository implements **two independent microservices** for PDF document parsing:

### 1. **Fast Parser Service** - PyMuPDF4LLM
- ⚡ **Ultra-fast**: 0.12s per document (~33 docs/second per pod)
- 🔧 **Python 3.13 no-GIL**: True thread parallelism with 4 concurrent workers
- 💻 **CPU-only**: No GPU required
- 📝 **Output**: Markdown text extraction
- 🎯 **Use Case**: Real-time text extraction for RAG pipelines

### 2. **Accurate Parser Service** - MinerU 2.5
- 🎯 **High-quality**: Multimodal extraction with layout preservation
- 🚀 **GPU-accelerated**: NVIDIA T4 for fast processing (1.70-2.12 pages/sec)
- 📊 **Rich output**: Markdown + images + tables + formulas
- 🔄 **Scale-to-zero**: Cost-efficient for batch processing
- 🎯 **Use Case**: High-fidelity document understanding for complex documents

---

## 🚧 Current Status: Planning Phase

**This repository is in the planning phase.** The architecture and implementation plan are complete, but the services are not yet implemented.

### What's Available Now:
- ✅ Comprehensive implementation plan ([PARSING_PLAN.md](PARSING_PLAN.md))
- ✅ AI assistant development guidance ([CLAUDE.md](CLAUDE.md))
- ✅ MinerU integrated as git submodule ([GIT_SUBMODULES.md](GIT_SUBMODULES.md))
- ✅ Architecture design and API specifications
- ✅ Repository structure and licensing (AGPL-3.0)

### Not Yet Implemented:
- ❌ Fast parser service (`fast/` directory)
- ❌ Accurate parser service (`accurate/` directory)
- ❌ Tests and benchmarks
- ❌ Docker images
- ❌ CI/CD pipelines

**Next Steps**: Begin implementation following [PARSING_PLAN.md](PARSING_PLAN.md) Week 1-4 roadmap.

---

## Architecture

### Service Separation

Both services are **completely independent** with different:
- Base images (Python 3.13-slim vs NVIDIA CUDA 11.8)
- Resource requirements (CPU-only vs GPU-required)
- Scaling strategies (always-on vs scale-to-zero)
- Endpoints and APIs
- Docker containers

### API Design

```http
POST /parse
Content-Type: multipart/form-data
Body: file=<binary PDF>

Response (synchronous):
{
  "markdown": "# Document Title\n\nContent...",
  "metadata": {
    "pages": 10,
    "processing_time_ms": 120,
    "parser": "pymupdf4llm|mineru",
    "version": "x.x.x"
  },
  "images": [...],     // Only accurate parser
  "tables": [...],     // Only accurate parser
  "formulas": [...]    // Only accurate parser
}
```

**No job management** - Services return results synchronously. Callers wait for response.

---

## MinerU Integration

This repository uses [MinerU](https://github.com/opendatalab/MinerU) as a **git submodule** for the accurate parser service.

### Quick Setup

```bash
# Clone repository with submodules
git clone --recurse-submodules https://github.com/YOUR_ORG/two_tier_document_parser.git
cd two_tier_document_parser

# Install MinerU for development
cd MinerU
pip install -e .[core]
mineru-models-download
cd ..
```

### Updating MinerU

```bash
# Update to latest MinerU version
cd MinerU
git pull origin master
cd ..

# Commit the update
git add MinerU
git commit -m "Update MinerU to latest version"
```

**Full Documentation**: See [GIT_SUBMODULES.md](GIT_SUBMODULES.md) for complete submodule usage, troubleshooting, and best practices.

---

## Quick Start (Once Implemented)

### Fast Parser Service

```bash
# Navigate to fast parser
cd fast/

# Install dependencies (Python 3.13 required)
pip install -r requirements.txt

# Run locally with no-GIL enabled
PYTHON_GIL=0 uvicorn app:app --host 0.0.0.0 --port 8004 --reload

# Test endpoint
curl -X POST http://localhost:8004/parse -F "file=@test.pdf"
```

### Accurate Parser Service

```bash
# Navigate to accurate parser
cd accurate/

# Install dependencies (Python 3.10 required)
pip install -r requirements.txt

# Download MinerU models (first time only)
python -c "from magic_pdf.model.download_models import download_models; download_models()"

# Run locally
uvicorn app:app --host 0.0.0.0 --port 8005 --reload

# Test endpoint (takes 1-3 minutes)
curl -X POST http://localhost:8005/parse -F "file=@test.pdf"
```

---

## Repository Structure (Planned)

```
two_tier_document_parser/
├── PARSING_PLAN.md            # Comprehensive implementation plan
├── CLAUDE.md                  # AI assistant development guidance
├── GIT_SUBMODULES.md         # Git submodule usage guide
├── LICENSE                    # AGPL-3.0 license
├── README.md                  # This file
├── MinerU/                    # Git submodule (MinerU repository)
├── fast/                      # Fast parser service (to be implemented)
│   ├── app.py                 # FastAPI app with ThreadPoolExecutor
│   ├── parser.py              # PyMuPDF4LLM wrapper
│   ├── models.py              # Pydantic request/response models
│   ├── Dockerfile             # python:3.13-slim base
│   └── requirements.txt       # Dependencies
├── accurate/                  # Accurate parser service (to be implemented)
│   ├── app.py                 # FastAPI app with ThreadPoolExecutor
│   ├── parser.py              # MinerU wrapper with image extraction
│   ├── models.py              # Pydantic request/response models
│   ├── Dockerfile             # nvidia/cuda:11.8.0-cudnn8-runtime base
│   └── requirements.txt       # Dependencies
└── tests/                     # Test suite (to be implemented)
    ├── fast/                  # Fast parser tests
    ├── accurate/              # Accurate parser tests
    └── integration/           # Integration tests
```

---

## Technology Stack

### Fast Parser
- **Python 3.13** with no-GIL mode (`PYTHON_GIL=0`)
- **FastAPI** 0.115.0+ for async endpoints
- **PyMuPDF4LLM** 0.0.17+ for PDF parsing
- **ThreadPoolExecutor** with 4 workers for concurrency
- **uvicorn** for ASGI server

### Accurate Parser
- **Python 3.10** (MinerU requirement)
- **FastAPI** 0.115.0+ for async endpoints
- **MinerU** (magic-pdf[full]) 0.8.0+ for multimodal parsing
- **CUDA 11.8** + cuDNN 8 for GPU acceleration
- **ThreadPoolExecutor** with 2 workers (GPU bottleneck)
- **uvicorn** for ASGI server

---

## Performance Targets

### Fast Parser
- **Latency**: <1 second per document (target: 0.12s)
- **Throughput**: 40 concurrent parses (10 pods × 4 workers)
- **Batch**: 100 documents in <30 seconds
- **Resources**: 4 vCPUs, 2-4Gi memory, no GPU

### Accurate Parser
- **Latency**: 1-3 minutes per document (GPU processing)
- **Throughput**: 1.70-2.12 pages/second
- **Cold start**: <60 seconds (GPU provisioning)
- **Resources**: 2 vCPUs, 16-32Gi memory, 1x NVIDIA T4 GPU

---

## License & IP Protection Strategy

### License: AGPL-3.0

This repository is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0), a strong copyleft license that requires:

- ✅ Source code disclosure for network services
- ✅ Same license for derivative works
- ✅ Public availability of modifications

**Compliance**: API responses include source code link and license information.

### IP Protection

**Public Repository** (this repo):
- Contains ONLY parsing service code (Docker images)
- Open-source under AGPL-3.0
- No proprietary business logic

**Private Repository** (`document_agent_v0.2`):
- Kubernetes manifests for deployment
- Compliance documentation
- Integration code with private application
- CI/CD pipelines
- Monitoring and network policies

**Strategy**: Git submodule integration separates public parsing code from private infrastructure, preventing accidental exposure of proprietary components.

---

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file - project overview and quick start |
| [PARSING_PLAN.md](PARSING_PLAN.md) | Comprehensive implementation plan (Week 1-4 roadmap) |
| [CLAUDE.md](CLAUDE.md) | AI assistant development guidance and patterns |
| [GIT_SUBMODULES.md](GIT_SUBMODULES.md) | Git submodule usage, troubleshooting, best practices |
| [LICENSE](LICENSE) | AGPL-3.0 license text |

---

## Development Guidelines

### Prerequisites

- **Python 3.13** (for fast parser development)
- **Python 3.10** (for accurate parser development)
- **Docker Desktop** (for containerized development)
- **NVIDIA GPU with CUDA 11.8+** (for accurate parser local testing, optional)
- **Google Cloud SDK** (for GCR image pushing, optional)

### Code Quality Standards

- ✅ Type hints on all functions
- ✅ Pydantic models for validation
- ✅ Structured JSON logging (no print statements)
- ✅ FastAPI automatic OpenAPI docs (`/docs` endpoint)
- ✅ Error handling with specific HTTP status codes
- ✅ pytest for unit and integration tests

### Code Size Targets

Keep implementations minimal and focused:
- **Fast parser**: ~150 lines total (app.py ~50, parser.py ~50, models.py ~30)
- **Accurate parser**: ~250 lines total (app.py ~60, parser.py ~100, models.py ~40)

---

## Contributing

Contributions are welcome! Please:

1. Review [PARSING_PLAN.md](PARSING_PLAN.md) for architecture and design decisions
2. Follow guidelines in [CLAUDE.md](CLAUDE.md) for development patterns
3. Write tests for new functionality
4. Ensure AGPL-3.0 compliance (include license headers)
5. Update documentation as needed

### Development Workflow

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Make changes following code quality standards
4. Test locally (unit tests + manual testing)
5. Build Docker image and test containerized
6. Submit pull request with description

---

## Deployment

**Note**: Kubernetes manifests and deployment configurations are in the **private repository** (`document_agent_v0.2`), not in this public repo.

Services are deployed to separate GKE namespaces:
- Fast parser: `parsing-fast` namespace
- Accurate parser: `parsing-accurate` namespace

Internal DNS:
- `http://fast-parser.parsing-fast.svc.cluster.local:8004`
- `http://accurate-parser.parsing-accurate.svc.cluster.local:8005`

---

## Roadmap

### Week 1: Public Repo Creation
- [ ] Implement fast parser (~150 lines)
- [ ] Implement accurate parser (~250 lines)
- [ ] Test Python 3.13 no-GIL locally
- [ ] Test concurrency (4 simultaneous requests)
- [ ] Write comprehensive README

### Week 2: Private Repo Integration
- [ ] Add git submodule to private repo
- [ ] Create K8s manifests
- [ ] Build and push images to GCR
- [ ] Deploy to GKE
- [ ] Verify cross-namespace communication

### Week 3: Backend Integration
- [ ] Implement ParsingServiceClient
- [ ] Update document routes
- [ ] Test E2E flow
- [ ] Test batch parsing
- [ ] Verify scale-to-zero

### Week 4: Production Readiness
- [ ] Setup monitoring
- [ ] Configure alerts
- [ ] Load testing
- [ ] Documentation review
- [ ] Final compliance check

---

## Support & Resources

- **Implementation Plan**: [PARSING_PLAN.md](PARSING_PLAN.md)
- **Development Guidance**: [CLAUDE.md](CLAUDE.md)
- **Submodule Guide**: [GIT_SUBMODULES.md](GIT_SUBMODULES.md)
- **MinerU Documentation**: [https://opendatalab.github.io/MinerU/](https://opendatalab.github.io/MinerU/)
- **PyMuPDF4LLM**: [https://github.com/pymupdf/pymupdf4llm](https://github.com/pymupdf/pymupdf4llm)

---

## Acknowledgments

- **MinerU** - High-quality PDF parsing with multimodal extraction ([opendatalab/MinerU](https://github.com/opendatalab/MinerU))
- **PyMuPDF4LLM** - Ultra-fast PDF to Markdown conversion ([pymupdf/pymupdf4llm](https://github.com/pymupdf/pymupdf4llm))

---

**License**: AGPL-3.0 | **Status**: Planning Phase | **Version**: 1.0 | **Last Updated**: November 2025
