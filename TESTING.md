# Testing Document Parsers on GCP GPU VM

This guide covers end-to-end testing of the two-tier document parser services on a GCP VM with NVIDIA T4 GPU.

## Table of Contents
- [Quick Start](#quick-start)
- [Setup Methods](#setup-methods)
  - [Method 1: Terraform (Recommended)](#method-1-terraform-recommended)
  - [Method 2: Manual gcloud](#method-2-manual-gcloud)
- [Testing Procedures](#testing-procedures)
- [Performance Benchmarks](#performance-benchmarks)
- [Troubleshooting](#troubleshooting)
- [Cost Management](#cost-management)

---

## Quick Start

**Prerequisites:**
- GCP account with billing enabled
- GPU quota (1x T4 GPU in your region)
- `gcloud` CLI installed and authenticated
- Terraform (optional, for automated setup)

**Total Setup Time:** ~10 minutes (driver installation takes 5-7 minutes)

---

## Setup Methods

### Method 1: Terraform (Recommended)

#### 1. Install Terraform

```bash
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Windows
choco install terraform
```

#### 2. Initialize Terraform

```bash
cd terraform/  # Or wherever you saved the .tf files

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
gcp_project_id = "your-project-id"
gcp_zone       = "us-central1-a"
instance_name  = "parser-gpu-test"
ssh_user       = "$(whoami)"
EOF

# Initialize
terraform init
```

#### 3. Review Plan

```bash
terraform plan
```

Expected resources:
- 1x Compute instance (n1-standard-4 + T4 GPU)
- 2x Firewall rules (SSH, parser ports)
- 1x 100GB SSD boot disk

**Estimated cost:** ~$0.54/hour (~$13/day if left running)

#### 4. Deploy

```bash
terraform apply
# Type 'yes' to confirm

# Save the output
# VM External IP: x.x.x.x
# SSH Command: gcloud compute ssh parser-gpu-test --zone=us-central1-a
```

#### 5. Connect

```bash
# Wait 2-3 minutes for startup script to complete
sleep 180

# SSH into VM
gcloud compute ssh parser-gpu-test --zone=us-central1-a

# Verify setup
nvidia-smi                          # GPU drivers
docker --version                    # Docker installed
docker run --rm --gpus all vllm/vllm-openai:v0.10.1.1 nvidia-smi  # GPU access
```

---

### Method 2: Manual gcloud

If you prefer not to use Terraform:

```bash
# Set project
gcloud config set project YOUR_PROJECT_ID

# Create VM
gcloud compute instances create parser-gpu-test \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd \
  --maintenance-policy=TERMINATE \
  --metadata=install-nvidia-driver=True \
  --tags=parser-test

# Allow SSH
gcloud compute firewall-rules create ssh-parser-test \
  --allow=tcp:22 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=parser-test

# Allow parser ports (optional)
gcloud compute firewall-rules create parser-ports \
  --allow=tcp:8004,tcp:8005 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=parser-test

# SSH
gcloud compute ssh parser-gpu-test --zone=us-central1-a

# Install dependencies manually
sudo apt-get update
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit docker-compose git
sudo systemctl restart docker

# Re-login for docker group
exit
gcloud compute ssh parser-gpu-test --zone=us-central1-a
```

---

## Testing Procedures

### 1. Clone Repository

```bash
# Clone with submodules (includes MinerU)
git clone --recurse-submodules https://github.com/YOUR_ORG/two_tier_document_parser.git
cd two_tier_document_parser
```

### 2. Option A: Test with Docker Compose (Both Services)

```bash
# Build and run both parsers
docker-compose up --build

# In another terminal (new SSH session)
gcloud compute ssh parser-gpu-test --zone=us-central1-a

# Get test PDF
curl -o test.pdf https://arxiv.org/pdf/2301.00000.pdf

# Test fast parser (CPU-only)
curl -X POST http://localhost:8004/parse \
  -F "file=@test.pdf" \
  -o fast_result.json

# Test accurate parser (GPU)
curl -X POST http://localhost:8005/parse \
  -F "file=@test.pdf" \
  -o accurate_result.json

# Compare results
cat fast_result.json | python3 -m json.tool
cat accurate_result.json | python3 -m json.tool
```

### 2. Option B: Test Accurate Parser Only

```bash
cd accurate/

# Build Docker image
docker build -t accurate-parser:test .

# Run with GPU
docker run --gpus all \
  -p 8005:8005 \
  -e LOG_LEVEL=DEBUG \
  --name accurate-parser \
  accurate-parser:test

# In another terminal, test
curl -o test.pdf https://arxiv.org/pdf/2301.00000.pdf

curl -X POST http://localhost:8005/parse \
  -F "file=@test.pdf" \
  -o result.json

cat result.json | python3 -m json.tool
```

### 3. Health Checks

```bash
# Fast parser
curl http://localhost:8004/health | python3 -m json.tool

# Expected:
# {
#   "status": "healthy",
#   "workers": 4,
#   "no_gil": true,
#   "parser": "pymupdf4llm",
#   "version": "0.0.17+"
# }

# Accurate parser
curl http://localhost:8005/health | python3 -m json.tool

# Expected:
# {
#   "status": "healthy",
#   "workers": 2,
#   "gpu_available": true,
#   "parser": "mineru",
#   "version": "2.6.4+"
# }
```

### 4. Monitor GPU Usage

```bash
# Real-time GPU monitoring
watch -n 1 nvidia-smi

# While parsing, you should see:
# - GPU Memory Usage: 2-4GB
# - GPU Utilization: 60-90%
# - Temperature: 50-70°C
```

### 5. Concurrency Testing

**Fast Parser (4 concurrent threads):**

```bash
# Create test script
cat > test_concurrency.sh <<'EOF'
#!/bin/bash
for i in {1..4}; do
  echo "Starting request $i..."
  curl -X POST http://localhost:8004/parse \
    -F "file=@test.pdf" \
    -o "result_$i.json" \
    -w "\nRequest $i: %{time_total}s\n" &
done
wait
echo "All requests complete"
EOF

chmod +x test_concurrency.sh
./test_concurrency.sh
```

**Accurate Parser (GPU queue):**

```bash
# Test 3 simultaneous requests (2 workers + 1 queued)
for i in {1..3}; do
  curl -X POST http://localhost:8005/parse \
    -F "file=@test.pdf" \
    -o "gpu_result_$i.json" \
    -w "\nGPU Request $i: %{time_total}s\n" &
done
wait
```

### 6. Performance Benchmarking

```bash
# Install Apache Bench
sudo apt-get install -y apache2-utils

# Fast parser benchmark (100 requests, 4 concurrent)
ab -n 100 -c 4 -p test.pdf -T 'multipart/form-data' \
  http://localhost:8004/parse

# Accurate parser benchmark (10 requests, 2 concurrent)
ab -n 10 -c 2 -p test.pdf -T 'multipart/form-data' \
  http://localhost:8005/parse
```

### 7. Memory Leak Testing

```bash
# Run same PDF 1000x
for i in {1..1000}; do
  curl -X POST http://localhost:8004/parse \
    -F "file=@test.pdf" > /dev/null

  if [ $((i % 100)) -eq 0 ]; then
    echo "Processed $i documents"
    docker stats --no-stream
  fi
done
```

### 8. Error Handling Tests

```bash
# Invalid file type (should return 400)
echo "not a pdf" > fake.pdf
curl -X POST http://localhost:8004/parse -F "file=@fake.pdf"

# Empty file (should return 400)
touch empty.pdf
curl -X POST http://localhost:8004/parse -F "file=@empty.pdf"

# Large file (should handle or return 413)
curl -o large.pdf https://example.com/100mb.pdf
curl -X POST http://localhost:8004/parse -F "file=@large.pdf"
```

---

## Performance Benchmarks

### Expected Results

**Fast Parser (PyMuPDF4LLM):**
- Single document: <1 second (target: 0.12s)
- 100 documents (4 concurrent): <30 seconds
- CPU utilization: 400% (4 cores fully utilized)
- Memory usage: 2-4GB

**Accurate Parser (MinerU):**
- Single document: 1-3 minutes (depends on page count)
- Processing speed: 1.70-2.12 pages/second
- GPU utilization: 60-90%
- GPU memory: 2-4GB
- System memory: 8-16GB

### Benchmark Script

```bash
#!/bin/bash

echo "=== Fast Parser Benchmark ==="
time for i in {1..10}; do
  curl -X POST http://localhost:8004/parse \
    -F "file=@test.pdf" > /dev/null 2>&1
done

echo -e "\n=== Accurate Parser Benchmark ==="
time curl -X POST http://localhost:8005/parse \
  -F "file=@test.pdf" > /dev/null 2>&1

echo -e "\n=== GPU Metrics ==="
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv
```

---

## Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA drivers
nvidia-smi

# If fails, manually install
sudo apt-get update
sudo apt-get install -y nvidia-driver-525
sudo reboot

# After reboot
nvidia-smi
```

### Docker Cannot Access GPU

```bash
# Reinstall NVIDIA Container Toolkit
sudo apt-get purge -y nvidia-container-toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Test
docker run --rm --gpus all vllm/vllm-openai:v0.10.1.1 nvidia-smi
```

### Out of Memory (OOM)

```bash
# Check memory usage
free -h
docker stats

# Increase VM memory (requires VM stop)
gcloud compute instances stop parser-gpu-test --zone=us-central1-a
gcloud compute instances set-machine-type parser-gpu-test \
  --machine-type=n1-standard-8 \
  --zone=us-central1-a
gcloud compute instances start parser-gpu-test --zone=us-central1-a
```

### Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :8004
sudo lsof -i :8005

# Kill process
sudo kill -9 <PID>

# Or stop Docker containers
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
```

### Slow Parsing Performance

```bash
# Check GPU utilization
nvidia-smi -l 1

# If GPU util is low (<50%), check:
# 1. CUDA version matches Dockerfile
docker run --rm --gpus all accurate-parser:test nvidia-smi

# 2. MinerU models downloaded
docker exec -it accurate-parser ls /root/.cache/huggingface/hub

# 3. Disk I/O (should use SSD)
sudo iostat -xz 1
```

---

## Cost Management

### Estimated Costs (us-central1-a)

| Resource | Cost/Hour | Cost/Day |
|----------|-----------|----------|
| n1-standard-4 | $0.19 | $4.56 |
| NVIDIA T4 GPU | $0.35 | $8.40 |
| 100GB SSD | $0.02 | $0.48 |
| **Total** | **$0.56** | **$13.44** |

### Cost Optimization

**1. Stop VM when not testing:**

```bash
# Stop (keeps disk, stops compute billing)
gcloud compute instances stop parser-gpu-test --zone=us-central1-a

# Start when needed
gcloud compute instances start parser-gpu-test --zone=us-central1-a
```

**2. Use preemptible instances (60-80% discount):**

```bash
# Add to Terraform or gcloud create command
--preemptible
```

⚠️ **Warning:** Preemptible VMs can be shut down at any time (max 24h runtime)

**3. Delete when testing complete:**

```bash
# Terraform
terraform destroy

# Or manual
gcloud compute instances delete parser-gpu-test --zone=us-central1-a
```

### Monitoring Costs

```bash
# View current month's costs
gcloud billing accounts list
gcloud beta billing projects describe YOUR_PROJECT_ID

# Set budget alerts in GCP Console:
# Billing → Budgets & Alerts → Create Budget
# - Set threshold: $50/month
# - Alert at 50%, 90%, 100%
```

---

## Testing Checklist

Before considering testing complete, verify:

- [ ] GPU drivers installed (`nvidia-smi` works)
- [ ] Docker has GPU access (`docker run --gpus all vllm/vllm-openai:v0.10.1.1 nvidia-smi`)
- [ ] Fast parser health check returns `"status": "healthy"`
- [ ] Accurate parser health check returns `"gpu_available": true`
- [ ] Fast parser completes single document in <1s
- [ ] Accurate parser completes single document in 1-3min
- [ ] Fast parser handles 4 concurrent requests without blocking
- [ ] Accurate parser utilizes GPU (>60% during parsing)
- [ ] No memory leaks (1000 document test shows stable memory)
- [ ] Error handling works (invalid file returns 400)
- [ ] Markdown output quality verified (manual inspection)
- [ ] Images extracted correctly (accurate parser only)
- [ ] Temporary files cleaned up (check `/tmp/`)

---

## Advanced Testing

### External Access Testing

If you want to test from your local machine (not SSH):

```bash
# Get VM external IP
gcloud compute instances describe parser-gpu-test \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Test from local machine
VM_IP=<external-ip>
curl -X POST http://$VM_IP:8004/parse -F "file=@local-test.pdf"
curl -X POST http://$VM_IP:8005/parse -F "file=@local-test.pdf"
```

### Load Testing

```bash
# Install hey (HTTP load testing tool)
sudo apt-get install -y hey

# Fast parser load test (100 requests, 10 concurrent)
hey -n 100 -c 10 -m POST \
  -T "multipart/form-data" \
  -D test.pdf \
  http://localhost:8004/parse

# Accurate parser load test (20 requests, 2 concurrent)
hey -n 20 -c 2 -m POST \
  -T "multipart/form-data" \
  -D test.pdf \
  http://localhost:8005/parse
```

### Profiling

```bash
# Install profiling tools
pip install py-spy memory_profiler

# CPU profiling (fast parser)
py-spy record --native -o fast_profile.svg -- python fast/app.py

# Memory profiling (accurate parser)
mprof run accurate/app.py
mprof plot
```

---

## Next Steps

After successful testing:

1. **Push images to GCR:**
   ```bash
   docker tag accurate-parser:test gcr.io/YOUR_PROJECT/accurate-parser:v1.0.0
   docker push gcr.io/YOUR_PROJECT/accurate-parser:v1.0.0
   ```

2. **Update Kubernetes manifests** (in private repo)

3. **Deploy to GKE** (see main deployment docs)

4. **Set up monitoring** (Prometheus, Grafana)

5. **Configure autoscaling** (HPA for both services)

---

**Last Updated:** November 2025
**Maintainer:** DevOps Team
**Related:** [DOCKER_SETUP.md](DOCKER_SETUP.md), [CLAUDE.md](CLAUDE.md), [PARSING_PLAN.md](PARSING_PLAN.md)
