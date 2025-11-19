"""
Accurate Parser Service - FastAPI application with MinerU.
"""
import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from models import ParseResponse, HealthResponse
from parser import parse_pdf

# Configure structured logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Accurate Parser Service",
    description="High-quality PDF parsing using MinerU with multimodal extraction",
    version="1.0.0"
)

# ThreadPoolExecutor for concurrent parsing
WORKERS = int(os.getenv("WORKERS", "2"))
executor = ThreadPoolExecutor(max_workers=WORKERS)

# Check GPU availability
try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
except ImportError:
    GPU_AVAILABLE = False

@app.on_event("startup")
async def startup_event():
    """
    Configure MinerU based on hardware availability.
    Generates magic-pdf.json dynamically.
    """
    import json
    from pathlib import Path
    
    config_path = Path("/root/magic-pdf.json")
    device_mode = "cuda" if GPU_AVAILABLE else "cpu"
    
    logger.info(f"Detected GPU availability: {GPU_AVAILABLE}. Setting MinerU device-mode to '{device_mode}'.")
    if GPU_AVAILABLE:
        try:
            logger.info(f"CUDA Version: {torch.version.cuda}")
            logger.info(f"CuDNN Version: {torch.backends.cudnn.version()}")
            logger.info(f"Device Name: {torch.cuda.get_device_name(0)}")
        except Exception as e:
            logger.warning(f"Could not get detailed GPU info: {e}")
    
    try:
        if config_path.exists():
            config = json.loads(config_path.read_text())
        else:
            config = {
                "bucket_info":{
                    "bucket-name": "bucket_name",
                    "access-key": "ak",
                    "secret-key": "sk",
                    "endpoint": "http://127.0.0.1:9000"
                },
                "models-dir": "/root/.cache/huggingface/hub",
                "table-config": {
                    "model": "TableMaster",
                    "is_table_recog_enable": True,
                    "max_time": 1200
                }
            }
            
        config["device-mode"] = device_mode
        config_path.write_text(json.dumps(config, indent=4))
        logger.info(f"Updated {config_path} with device-mode: {device_mode}")
        
    except Exception as e:
        logger.error(f"Failed to update magic-pdf.json: {e}")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        workers=WORKERS,
        gpu_available=GPU_AVAILABLE
    )


@app.post("/parse", response_model=ParseResponse)
async def parse(file: UploadFile = File(...)) -> ParseResponse:
    """
    Parse PDF file to markdown with images, tables, and formulas.

    Args:
        file: PDF file upload

    Returns:
        ParseResponse with markdown content, images, tables, formulas, and metadata
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read file content
    try:
        pdf_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read file")

    # Validate file size (500MB limit for accurate parser)
    if len(pdf_bytes) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 500MB)")

    # Parse PDF in thread pool
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            parse_pdf,
            pdf_bytes,
            file.filename
        )

        logger.info(
            f'{{"filename": "{file.filename}", "pages": {result["metadata"]["pages"]}, '
            f'"processing_time_ms": {result["metadata"]["processing_time_ms"]}, '
            f'"images": {len(result["images"])}, "tables": {len(result["tables"])}, '
            f'"formulas": {len(result["formulas"])}}}'
        )

        return ParseResponse(**result)

    except Exception as e:
        logger.error(f"Parsing failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


# Import asyncio for event loop
import asyncio


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
