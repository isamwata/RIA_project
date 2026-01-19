"""
PDF Extractor for RIA Project using Google Cloud Document AI

This module provides PDF extraction using Google Cloud Document AI only.
Supports both synchronous processing (≤30 pages) and batch processing (>30 pages).

Usage:
    from backend.pdf_extractor import PDFExtractor
    
    extractor = PDFExtractor()
    result = extractor.extract("path/to/document.pdf")
    print(result["text"])
"""

import os
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Try to import Document AI service
try:
    from .document_ai_service import DocumentAIService, create_service_from_env
    DOCUMENT_AI_AVAILABLE = True
except ImportError:
    DOCUMENT_AI_AVAILABLE = False
    raise ImportError(
        "Document AI service not available. "
        "Install with: pip install google-cloud-documentai"
    )


class PDFExtractor:
    """
    PDF extractor using Google Cloud Document AI only.
    """
    
    def __init__(self):
        """
        Initialize PDF extractor with Document AI.
        
        Raises:
            RuntimeError: If Document AI is not configured
        """
        if not DOCUMENT_AI_AVAILABLE:
            raise RuntimeError(
                "Document AI is not available. "
                "Install with: pip install google-cloud-documentai"
            )
        
        self.doc_ai_service = None
        try:
            self.doc_ai_service = create_service_from_env()
            if not self.doc_ai_service:
                raise RuntimeError(
                    "Document AI service not configured. "
                    "Set GCP_PROJECT_ID, DOCUMENT_AI_PROCESSOR_ID, and GCP_CREDENTIALS_PATH in .env file."
                )
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Document AI: {e}. "
                "Check your .env configuration."
            )
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text and structure from PDF using Document AI.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Dictionary containing:
            - text: Extracted text
            - method: Extraction method used
            - pages: Page information
            - tables: Extracted tables
            - entities: Extracted entities
            - metadata: Additional metadata
        
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If Document AI processing fails
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Extracting with Document AI: {pdf_path}")
        result = self._extract_with_document_ai(pdf_path)
        result["method"] = "document_ai"
        return result
    
    def _extract_with_document_ai(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract using Document AI, automatically using chunking or batch processing for large documents."""
        import os
        import fitz
        
        # Check document size first
        pdf_doc = fitz.open(pdf_path)
        page_count = len(pdf_doc)
        pdf_doc.close()
        
        # Use batch processing or chunking for documents > 30 pages (OCR Processor limit)
        use_advanced = page_count > 30
        
        if use_advanced:
            gcs_bucket = os.getenv("GCS_BUCKET_NAME")
            
            if gcs_bucket:
                # Use batch processing (requires GCS)
                print(f"   📦 Using batch processing (document has {page_count} pages)...")
                result = self.doc_ai_service.process_document_batch(
                    str(pdf_path),
                    gcs_bucket=gcs_bucket
                )
            else:
                # Use chunking approach (no GCS required)
                # WARNING: Chunking may compromise document flow and context
                print(f"   ⚠️  Document has {page_count} pages (exceeds 30-page limit)")
                print(f"   ⚠️  WARNING: Chunking may break document flow (tables, references, context)")
                print(f"   💡 Recommendation: Set GCS_BUCKET_NAME in .env for batch processing (preserves full context)")
                print(f"   🔀 Splitting into chunks and processing with Document AI...")
                from .document_ai_large_docs import LargeDocumentAIService
                
                # Create large document service with same config
                large_service = LargeDocumentAIService(
                    project_id=self.doc_ai_service.project_id,
                    location=self.doc_ai_service.location,
                    processor_id=self.doc_ai_service.processor_id,
                    credentials_path=os.getenv("GCP_CREDENTIALS_PATH")
                )
                # Use same client
                large_service.client = self.doc_ai_service.client
                large_service.processor_name = self.doc_ai_service.processor_name
                
                result = large_service.process_large_document(str(pdf_path))
        else:
            # Use regular processing for smaller documents
            result = self.doc_ai_service.process_document(str(pdf_path))
        
        return {
            "text": result["text"],
            "pages": result["pages"],
            "tables": result.get("tables", []),
            "form_fields": result.get("form_fields", {}),
            "entities": result.get("entities", []),
            "layout": result.get("layout", {}),
            "metadata": result.get("metadata", {})
        }
    
    
    def batch_extract(self, pdf_paths: list) -> list:
        """
        Extract multiple PDFs.
        
        Args:
            pdf_paths: List of PDF file paths
        
        Returns:
            List of extraction results
        """
        results = []
        for pdf_path in pdf_paths:
            try:
                result = self.extract(pdf_path)
                results.append({
                    "file": str(pdf_path),
                    "status": "success",
                    "data": result
                })
            except Exception as e:
                results.append({
                    "file": str(pdf_path),
                    "status": "error",
                    "error": str(e)
                })
        return results


# Convenience function
def extract_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Convenience function to extract PDF using Document AI.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Extraction result dictionary
    """
    extractor = PDFExtractor()
    return extractor.extract(pdf_path)
