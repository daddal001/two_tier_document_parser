"""
Pydantic models for Accurate Parser Service.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ImageData(BaseModel):
    """Model for extracted images."""
    image_id: str = Field(..., description="Unique image identifier")
    image_base64: str = Field(..., description="Base64-encoded PNG image")
    page: int = Field(..., description="Page number where image was found")
    bbox: Optional[List[float]] = Field(None, description="Bounding box [x0, y0, x1, y1]")


class TableData(BaseModel):
    """Model for extracted tables."""
    table_id: str = Field(..., description="Unique table identifier")
    markdown: str = Field(..., description="Table in markdown format")
    page: int = Field(..., description="Page number where table was found")
    bbox: Optional[List[float]] = Field(None, description="Bounding box [x0, y0, x1, y1]")


class FormulaData(BaseModel):
    """Model for extracted formulas."""
    formula_id: str = Field(..., description="Unique formula identifier")
    latex: str = Field(..., description="Formula in LaTeX format")
    page: int = Field(..., description="Page number where formula was found")
    bbox: Optional[List[float]] = Field(None, description="Bounding box [x0, y0, x1, y1]")


class ParseResponse(BaseModel):
    """Response model for PDF parsing."""
    markdown: str = Field(..., description="Extracted markdown content")
    metadata: dict = Field(..., description="Parsing metadata")
    images: List[ImageData] = Field(default_factory=list, description="Extracted images")
    tables: List[TableData] = Field(default_factory=list, description="Extracted tables")
    formulas: List[FormulaData] = Field(default_factory=list, description="Extracted formulas")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    workers: int = Field(..., description="Number of ThreadPool workers")
    gpu_available: bool = Field(..., description="Whether GPU is available")
    parser: str = Field(default="mineru", description="Parser library name")
    version: str = Field(default="1.0.0", description="Service version")
