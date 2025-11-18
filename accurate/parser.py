"""
MinerU wrapper for accurate PDF parsing with multimodal extraction.
"""
import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List
import os


def parse_pdf(pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse PDF using MinerU with full multimodal extraction.

    Args:
        pdf_bytes: PDF file content as bytes
        filename: Original filename for logging

    Returns:
        Dictionary with markdown, images, tables, formulas, and metadata
    """
    start_time = time.time()

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pdf_path = tmp_path / "input.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)

        # Write PDF to temporary file
        pdf_path.write_bytes(pdf_bytes)

        try:
            # Import MinerU components
            from magic_pdf.pipe.UNIPipe import UNIPipe
            from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter
            import magic_pdf.model as model_config

            # Configure model paths
            model_config.__use_inside_model__ = True

            # Initialize reader/writer
            image_writer = DiskReaderWriter(str(output_dir))

            # Read PDF bytes
            jso_useful_key = {"_pdf_type": "", "model_list": []}

            # Initialize UNIPipe for parsing
            pipe = UNIPipe(
                pdf_bytes,
                jso_useful_key,
                image_writer,
                is_debug=False
            )

            # Run pipeline
            pipe.pipe_classify()
            pipe.pipe_analyze()
            pipe.pipe_parse()

            # Get content dictionary
            content_dict = pipe.pipe_mk_uni_format(
                str(output_dir),
                drop_mode="none"
            )

            # Extract markdown
            markdown_text = pipe.pipe_mk_markdown(
                str(output_dir),
                drop_mode="none"
            )

            # Extract images
            images = []
            image_dir = output_dir / "images"
            if image_dir.exists():
                for idx, img_file in enumerate(sorted(image_dir.glob("*.png"))):
                    with open(img_file, "rb") as f:
                        img_base64 = base64.b64encode(f.read()).decode('utf-8')
                    images.append({
                        "image_id": f"img_{idx}",
                        "image_base64": img_base64,
                        "page": 0,  # MinerU provides page info in content_dict
                        "bbox": None
                    })

            # Extract tables from markdown (simplified - MinerU embeds tables in markdown)
            tables = []
            # Tables are embedded in the markdown output by MinerU

            # Extract formulas (simplified - MinerU embeds formulas in markdown)
            formulas = []
            # Formulas are embedded in the markdown output by MinerU

            # Get page count
            import pymupdf
            with pymupdf.open(pdf_path) as doc:
                page_count = len(doc)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "markdown": markdown_text,
                "metadata": {
                    "pages": page_count,
                    "processing_time_ms": processing_time_ms,
                    "parser": "mineru",
                    "version": "2.5.0",
                    "filename": filename,
                    "source_code": "https://github.com/daddal001/two_tier_document_parser",
                    "license": "AGPL-3.0"
                },
                "images": images,
                "tables": tables,
                "formulas": formulas
            }

        except Exception as e:
            # Fallback to basic parsing if MinerU fails
            print(f"MinerU parsing failed: {e}, falling back to basic extraction")

            # Basic fallback using PyMuPDF
            import pymupdf
            with pymupdf.open(pdf_path) as doc:
                page_count = len(doc)
                text = ""
                for page in doc:
                    text += page.get_text()

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "markdown": text,
                "metadata": {
                    "pages": page_count,
                    "processing_time_ms": processing_time_ms,
                    "parser": "mineru_fallback",
                    "version": "1.0.0",
                    "filename": filename,
                    "error": str(e),
                    "source_code": "https://github.com/daddal001/two_tier_document_parser",
                    "license": "AGPL-3.0"
                },
                "images": [],
                "tables": [],
                "formulas": []
            }
