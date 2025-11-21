"""
Pydantic models for Fast Parser Service.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ParseResponse(BaseModel):
    """Response model for PDF parsing."""
    markdown: str = Field(..., description="Extracted markdown content")
    metadata: dict = Field(..., description="Parsing metadata")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    workers: int = Field(..., description="Number of ThreadPool workers")
    no_gil: bool = Field(..., description="Whether Python no-GIL mode is enabled")
    parser: str = Field(default="pymupdf4llm", description="Parser library name")
    version: str = Field(default="1.0.0", description="Service version")
