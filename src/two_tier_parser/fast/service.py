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
    Parse PDF using PyMuPDF4LLM with page-by-page error recovery.

    If individual pages cause errors (e.g., table detection bug), skip those pages
    and continue parsing the rest of the document.

    Args:
        pdf_bytes: PDF file content as bytes
        filename: Original filename for logging

    Returns:
        Dictionary with markdown content and metadata.
        Metadata includes 'skipped_pages' list if any pages failed to parse.
    """
    start_time = time.time()

    # Create temporary file for PDF processing
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        tmp_file.write(pdf_bytes)

    try:
        import pymupdf

        # Get page count first
        with pymupdf.open(tmp_path) as doc:
            total_pages = len(doc)

        # Try parsing all pages at once first (fastest path)
        try:
            markdown_text = pymupdf4llm.to_markdown(str(tmp_path))
            skipped_pages = []

        except AttributeError as e:
            # Table detection bug - parse page by page
            if "'NoneType' object has no attribute 'tables'" in str(e):
                markdown_parts = []
                skipped_pages = []

                for page_num in range(total_pages):
                    try:
                        # Parse single page
                        page_md = pymupdf4llm.to_markdown(
                            str(tmp_path),
                            pages=[page_num]  # Single page
                        )
                        markdown_parts.append(page_md)

                    except AttributeError as page_error:
                        # Skip this problematic page
                        if "'NoneType' object has no attribute 'tables'" in str(page_error):
                            skipped_pages.append(page_num + 1)  # 1-indexed for user
                            # Add placeholder for skipped page
                            markdown_parts.append(
                                f"\n\n---\n**[Page {page_num + 1} skipped due to parsing error]**\n---\n\n"
                            )
                        else:
                            raise  # Different error, re-raise

                markdown_text = "\n\n".join(markdown_parts)
            else:
                raise  # Different AttributeError, re-raise

        processing_time_ms = int((time.time() - start_time) * 1000)

        result = {
            "markdown": markdown_text,
            "metadata": {
                "pages": total_pages,
                "processing_time_ms": processing_time_ms,
                "parser": "pymupdf4llm",
                "version": "0.2.0",
                "filename": filename
            }
        }

        # Add skipped pages info if any
        if skipped_pages:
            result["metadata"]["skipped_pages"] = skipped_pages
            result["metadata"]["warning"] = f"Skipped {len(skipped_pages)} page(s) due to parsing errors"

        return result

    finally:
        # Clean up temporary file
        tmp_path.unlink(missing_ok=True)
