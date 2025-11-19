"""
MinerU wrapper for accurate PDF parsing with multimodal extraction.
Using MinerU v2.6.4+
"""
import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List
import os
from loguru import logger

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
            # New API in MinerU 2.x
            from mineru.cli.common import do_parse, read_fn
            from mineru.version import __version__

            # We use 'pipeline' backend as it's the most robust for standalone usage without complex VLLM server setup
            # But if the environment has GPUs and VLLM support (which the Dockerfile suggests),
            # 'vlm-transformers' might be better if we want VLM capabilities without external server.
            # However, 'pipeline' is the safe default in the official CLI.
            
            # NOTE: docker-compose uses vllm-server separate service. 
            # If we want to use that, we should use 'vlm-http-client' backend.
            # But here we are running inside a standalone container.
            # Given the user wants "accurate" parser and we are based on vllm image,
            # let's try 'pipeline' first as it is self-contained and simpler to invoke via python API.
            # The 'vlm' backend in 2.x is complex to invoke directly via do_parse without a running server or heavy setup.
            
            # Let's stick to 'pipeline' for now as it provides the structured output we need.
            # If 'vlm-transformers' is stable, we could try that too.
            backend = 'pipeline' 
            
            # Configure arguments for do_parse
            # We need to pass lists as do_parse expects batch processing
            do_parse(
                output_dir=str(output_dir),
                pdf_file_names=[filename.rsplit('.', 1)[0]], # Remove extension for folder name
                pdf_bytes_list=[pdf_bytes],
                p_lang_list=['ch'], # Default to 'ch' (auto detection is better but API asks for list)
                backend=backend,
                parse_method='auto',
                formula_enable=True,
                table_enable=True,
                f_dump_md=True,
                f_dump_middle_json=True,
                f_dump_content_list=True,
                f_dump_orig_pdf=False
            )

            # Result directory name is derived from filename
            result_dir_name = filename.rsplit('.', 1)[0]
            result_dir = output_dir / result_dir_name / "auto" # 'auto' is the parse_method
            
            # Check if result directory exists
            if not result_dir.exists():
                # Fallback to checking just the name if 'auto' subdir isn't created (depends on version)
                result_dir = output_dir / result_dir_name
            
            logger.info(f"Checking for images in: {result_dir / 'images'}")
            if not (result_dir / "images").exists():
                logger.warning(f"Image directory not found. Contents of {result_dir}: {list(result_dir.glob('*')) if result_dir.exists() else 'Dir not found'}")
            
            # Read content list (structured output)
            content_list_path = result_dir / f"{result_dir_name}_content_list.json"
            markdown_path = result_dir / f"{result_dir_name}.md"
            
            markdown_text = ""
            if markdown_path.exists():
                markdown_text = markdown_path.read_text(encoding='utf-8')
            
            # Extract images
            images = []
            image_dir = result_dir / "images"
            if image_dir.exists():
                for idx, img_file in enumerate(sorted(image_dir.glob("*"))):
                    if img_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                        with open(img_file, "rb") as f:
                            img_base64 = base64.b64encode(f.read()).decode('utf-8')
                        images.append({
                            "image_id": img_file.name,
                            "image_base64": img_base64,
                            "page": 0, # Placeholder
                            "bbox": None
                        })

            # Tables and Formulas are embedded in the content/markdown
            # We could parse content_list.json to extract them explicitly if needed
            tables = []
            formulas = []
            
            if content_list_path.exists():
                content_data = json.loads(content_list_path.read_text(encoding='utf-8'))
                # We could iterate over content_data to find tables/formulas if structured extraction is needed
                # For now, we follow the previous pattern of embedding them in MD
            
            # Get page count using pymupdf (still useful for metadata)
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(pdf_bytes)
            page_count = len(pdf)
            pdf.close()

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "markdown": markdown_text,
                "metadata": {
                    "pages": page_count,
                    "processing_time_ms": processing_time_ms,
                    "parser": "mineru",
                    "version": __version__,
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
            import traceback
            tb = traceback.format_exc()
            logger.error(f"MinerU parsing failed: {e}\nTraceback: {tb}")
            
            # Basic fallback using pypdfium2 (since we have it for MinerU)
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(pdf_bytes)
            page_count = len(pdf)
            text = ""
            for page in pdf:
                text_page = page.get_textpage()
                text += text_page.get_text_range() + "\n\n"
                text_page.close()
            pdf.close()

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "markdown": text,
                "metadata": {
                    "pages": page_count,
                    "processing_time_ms": processing_time_ms,
                    "parser": "mineru_fallback",
                    "version": "1.0.0",
                    "filename": filename,
                    "error": f"{e}\n{tb}",
                    "source_code": "https://github.com/daddal001/two_tier_document_parser",
                    "license": "AGPL-3.0"
                },
                "images": [],
                "tables": [],
                "formulas": []
            }
