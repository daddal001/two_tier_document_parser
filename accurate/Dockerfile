# Accurate Parser Service Dockerfile
# Based on official MinerU configuration

FROM vllm/vllm-openai:v0.10.1.1

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

# Set working directory
WORKDIR /app

# Copy requirements
COPY accurate/requirements.txt .

# Install python dependencies (FastAPI, uvicorn, etc.)
# We use --break-system-packages because we are in a container and want to install to system python
RUN python3 -m pip install -r requirements.txt --break-system-packages

# Copy local MinerU submodule and install it
COPY MinerU /tmp/MinerU
RUN python3 -m pip install -e /tmp/MinerU[core] --break-system-packages

# Download MinerU models
# Using HuggingFace source as per official Dockerfile
RUN /bin/bash -c "mineru-models-download -s huggingface -m all"

# Copy application code
COPY accurate/app.py accurate/parser.py accurate/models.py accurate/magic-pdf.json ./

# Copy config to user home for MinerU
RUN cp magic-pdf.json /root/magic-pdf.json

# Set environment variables
ENV WORKERS=2
ENV LOG_LEVEL=INFO
ENV CUDA_VISIBLE_DEVICES=0
ENV MINERU_MODEL_SOURCE=local
ENV MINERU_VLM_FORMULA_ENABLE=True
ENV MINERU_VLM_TABLE_ENABLE=True
ENV MINERU_ENABLE_FORMULA=True

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8005/health')"

# Reset entrypoint to override base image
ENTRYPOINT []

# Run application
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8005"]
