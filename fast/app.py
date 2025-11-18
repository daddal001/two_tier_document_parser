"""
Fast Parser Service - FastAPI application with PyMuPDF4LLM.
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
    title="Fast Parser Service",
    description="Ultra-fast PDF parsing using PyMuPDF4LLM",
    version="1.0.0"
)

# ThreadPoolExecutor for concurrent parsing
WORKERS = int(os.getenv("WORKERS", "4"))
executor = ThreadPoolExecutor(max_workers=WORKERS)

# Check if no-GIL mode is enabled
NO_GIL = os.getenv("PYTHON_GIL") == "0"


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        workers=WORKERS,
        no_gil=NO_GIL
    )


@app.post("/parse", response_model=ParseResponse)
async def parse(file: UploadFile = File(...)) -> ParseResponse:
    """
    Parse PDF file to markdown.

    Args:
        file: PDF file upload

    Returns:
        ParseResponse with markdown content and metadata
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

    # Validate file size (100MB limit)
    if len(pdf_bytes) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")

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
            f'"processing_time_ms": {result["metadata"]["processing_time_ms"]}}}'
        )

        return ParseResponse(**result)

    except Exception as e:
        logger.error(f"Parsing failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Parsing failed")


# Import asyncio for event loop
import asyncio


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
