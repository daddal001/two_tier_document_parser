"""
PyMuPDF4LLM wrapper for fast PDF parsing.
"""
import tempfile
import time
from pathlib import Path
from typing import Dict, Any
import pymupdf4llm


def parse_pdf(pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse PDF using PyMuPDF4LLM.

    Args:
        pdf_bytes: PDF file content as bytes
        filename: Original filename for logging

    Returns:
        Dictionary with markdown content and metadata
    """
    start_time = time.time()

    # Create temporary file for PDF processing
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        tmp_file.write(pdf_bytes)

    try:
        # Parse PDF to markdown
        markdown_text = pymupdf4llm.to_markdown(str(tmp_path))

        # Get page count
        import pymupdf
        with pymupdf.open(tmp_path) as doc:
            page_count = len(doc)

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "markdown": markdown_text,
            "metadata": {
                "pages": page_count,
                "processing_time_ms": processing_time_ms,
                "parser": "pymupdf4llm",
                "version": "0.2.0",
                "filename": filename,
                "source_code": "https://github.com/daddal001/two_tier_document_parser",
                "license": "AGPL-3.0"
            }
        }
    finally:
        # Clean up temporary file
        tmp_path.unlink(missing_ok=True)
