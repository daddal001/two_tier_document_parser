# Docker Setup Guide

This guide explains how to run the two-tier document parser using Docker Compose and visualize results with Jupyter notebooks.

## Prerequisites

- Docker Desktop (with Docker Compose)
- For GPU support (accurate parser): NVIDIA GPU with drivers + nvidia-docker
- Python 3.8+ (for Jupyter notebook)
- At least 8GB RAM (16GB recommended for accurate parser)

## Quick Start

### 1. Build and Start Services

```bash
# Build and start both parser services
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d
```

This will start:
- **Fast Parser** on `http://localhost:8004`
- **Accurate Parser** on `http://localhost:8005`

### 2. Verify Services are Running

```bash
# Check fast parser health
curl http://localhost:8004/health

# Check accurate parser health
curl http://localhost:8005/health
```

Expected output:
```json
{
  "status": "healthy",
  "workers": 4,
  "no_gil": true,
  "parser": "pymupdf4llm",
  "version": "1.0.0"
}
```

### 3. Test Parsing

```bash
# Parse a PDF with fast parser
curl -X POST http://localhost:8004/parse \
  -F "file=@/path/to/your/document.pdf" \
  > fast_result.json

# Parse a PDF with accurate parser (takes longer)
curl -X POST http://localhost:8005/parse \
  -F "file=@/path/to/your/document.pdf" \
  > accurate_result.json
```

## Using the Jupyter Notebook

### 1. Install Notebook Dependencies

### Create venv

```bash
python3 -m venv venv
```

### activate venv
```bash
source venv/bin/activate
or
.\venv\Scripts\Activate.ps1
```

### Install Notebook Dependencies
```bash
pip install -r notebook_requirements.txt
```

### 2. Launch Jupyter Lab

```bash
jupyter lab
```

### 3. Open the Visualization Notebook

1. Navigate to `parser_visualization.ipynb`
2. Update the `PDF_FILE_PATH` variable with your PDF file path
3. Run all cells to see comprehensive visualizations

The notebook will:
- ✅ Check health of both services
- ✅ Parse your PDF with both parsers
- ✅ Display metadata, markdown, images, tables, and formulas
- ✅ Compare performance metrics
- ✅ Export results to JSON and markdown files

## Docker Compose Configuration

### Service: fast-parser

- **Port**: 8004
- **Base Image**: python:3.13-slim
- **CPU**: 4 cores
- **Memory**: 2-4GB
- **No-GIL Mode**: Enabled for true thread parallelism
- **Workers**: 4 concurrent threads

### Service: accurate-parser

- **Port**: 8005
- **Base Image**: vllm/vllm-openai:v0.10.1.1
- **CPU**: 2 cores
- **Memory**: 8-16GB
- **GPU**: Optional (uncomment in docker-compose.yml)
- **Workers**: 2 concurrent threads

## Enabling GPU Support (Accurate Parser)

### 1. Install nvidia-docker

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### 2. Uncomment GPU Configuration in docker-compose.yml

Edit `docker-compose.yml` and uncomment:

```yaml
accurate-parser:
  # ...
  runtime: nvidia
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### 3. Verify GPU Access

```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base nvidia-smi
```

## Troubleshooting

### Fast Parser Issues

**Issue**: "PYTHON_GIL not disabled"
```bash
# Verify environment variable in container
docker exec fast-parser env | grep PYTHON_GIL
# Should output: PYTHON_GIL=0
```

**Issue**: Port 8004 already in use
```bash
# Change port in docker-compose.yml
ports:
  - "8014:8004"  # Use port 8014 instead
```

### Accurate Parser Issues

**Issue**: Out of memory
```bash
# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 16G  # Increase to 16GB or 32GB
```

**Issue**: CUDA not available
```bash
# Check if GPU is accessible
docker exec accurate-parser python -c "import torch; print(torch.cuda.is_available())"
```

**Issue**: MinerU model download failed
```bash
# Manually download models in container
docker exec accurate-parser mineru-models-download -s huggingface -m all
```

### General Issues

**Issue**: Containers won't start
```bash
# Check logs
docker-compose logs fast-parser
docker-compose logs accurate-parser

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

**Issue**: Slow parsing performance
```bash
# Check resource usage
docker stats

# Ensure enough resources allocated in Docker Desktop settings
# Recommended: 4+ CPUs, 8+ GB RAM
```

## Stopping Services

```bash
# Stop services (preserve containers)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes
docker-compose down -v

# Stop and remove everything including images
docker-compose down --rmi all -v
```

## Development Mode

For development with auto-reload:

```bash
# Fast parser
cd fast/
PYTHON_GIL=0 uvicorn app:app --host 0.0.0.0 --port 8004 --reload

# Accurate parser
cd accurate/
uvicorn app:app --host 0.0.0.0 --port 8005 --reload
```

## Production Deployment

See the private `document_agent_v0.2` repository for:
- Kubernetes manifests
- Horizontal Pod Autoscaling configuration
- Network policies
- Monitoring setup
- CI/CD workflows

## API Documentation

Once services are running, interactive API docs are available at:

- Fast Parser: http://localhost:8004/docs
- Accurate Parser: http://localhost:8005/docs

## Performance Benchmarks

### Fast Parser (PyMuPDF4LLM)

- **Latency**: 100-500ms per document
- **Throughput**: ~33 documents/second per pod (4 workers)
- **Concurrency**: 4 simultaneous parses (no-GIL mode)
- **Best for**: Quick text extraction, high-volume processing

### Accurate Parser (MinerU)

- **Latency**: 1-3 minutes per document
- **Throughput**: 1.70-2.12 pages/second
- **Concurrency**: 2 workers (GPU bottleneck)
- **Best for**: Documents with images, tables, formulas
- **Base**: vLLM/OpenAI (MinerU 2.6.4+)

## License

AGPL-3.0 - See LICENSE file

Source code: https://github.com/daddal001/two_tier_document_parser

## Support

For issues or questions:
1. Check this guide's troubleshooting section
2. Review logs: `docker-compose logs`
3. Open an issue on GitHub
