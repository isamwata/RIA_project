"""
Document AI Service for RIA Project

This service provides integration with Google Cloud Document AI for enhanced
PDF extraction, including OCR, structured data extraction, and layout analysis.

Usage:
    from backend.document_ai_service import DocumentAIService
    
    service = DocumentAIService(
        project_id="your-project-id",
        location="us",
        processor_id="your-processor-id",
        credentials_path="./credentials/service-account.json"
    )
    
    result = service.process_document("path/to/document.pdf")
    print(result["text"])
    print(result["tables"])
    print(result["entities"])
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

try:
    from google.cloud import documentai
    from google.oauth2 import service_account
    DOCUMENT_AI_AVAILABLE = True
except ImportError:
    DOCUMENT_AI_AVAILABLE = False
    print("Warning: google-cloud-documentai not installed. Install with: pip install google-cloud-documentai")


class DocumentAIService:
    """
    Service for processing documents using Google Cloud Document AI.
    
    Provides:
    - High-accuracy OCR
    - Structured data extraction (tables, forms)
    - Layout analysis
    - Entity extraction
    """
    
    def __init__(
        self,
        project_id: str,
        location: str = "us",
        processor_id: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize Document AI service.
        
        Args:
            project_id: Google Cloud project ID
            location: Processor location (us, eu, etc.)
            processor_id: Document AI processor ID (optional, uses OCR processor if not provided)
            credentials_path: Path to service account JSON credentials
        """
        if not DOCUMENT_AI_AVAILABLE:
            raise ImportError(
                "google-cloud-documentai is not installed. "
                "Install with: pip install google-cloud-documentai"
            )
        
        # Load credentials
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
        else:
            # Try to use default credentials
            credentials = None
        
        self.client = documentai.DocumentProcessorServiceClient(
            credentials=credentials
        )
        
        self.project_id = project_id
        self.location = location
        
        # Use OCR processor by default if processor_id not provided
        if processor_id:
            self.processor_id = processor_id
        else:
            # Default to OCR processor
            # Note: You need to create this processor in GCP Console
            self.processor_id = None
        
        self.processor_name = None
        if self.processor_id:
            self.processor_name = self.client.processor_path(
                project_id, location, processor_id
            )
    
    def process_document_batch(
        self,
        pdf_path: str,
        gcs_bucket: str,
        gcs_prefix: str = "document-ai-temp",
        mime_type: str = "application/pdf",
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Process a large document using Document AI Batch Processing API.
        This method can handle documents up to 200 pages (or 500 for Layout Parser).
        
        Args:
            pdf_path: Path to PDF file
            gcs_bucket: Google Cloud Storage bucket name
            gcs_prefix: GCS prefix/folder for temporary files
            mime_type: MIME type of the document
            timeout: Timeout in seconds for batch processing
        
        Returns:
            Dictionary containing extracted text and structure
        """
        from google.cloud import storage
        import time
        import uuid
        
        if not self.processor_name:
            raise ValueError("Processor not configured.")
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Initialize GCS client
        storage_client = storage.Client(credentials=self.client._credentials if hasattr(self.client, '_credentials') else None)
        bucket = storage_client.bucket(gcs_bucket)
        
        # Upload PDF to GCS
        gcs_filename = f"{gcs_prefix}/{uuid.uuid4()}_{pdf_path.name}"
        blob = bucket.blob(gcs_filename)
        
        print(f"📤 Uploading PDF to GCS: gs://{gcs_bucket}/{gcs_filename}")
        blob.upload_from_filename(str(pdf_path))
        gcs_uri = f"gs://{gcs_bucket}/{gcs_filename}"
        
        try:
            # Create batch process request
            input_config = documentai.BatchProcessRequest.BatchInputConfig(
                gcs_source=gcs_uri,
                mime_type=mime_type
            )
            
            output_config = documentai.BatchProcessRequest.BatchOutputConfig(
                gcs_destination=f"gs://{gcs_bucket}/{gcs_prefix}/output/"
            )
            
            batch_request = documentai.BatchProcessRequest(
                name=self.processor_name,
                input_configs=[input_config],
                output_config=output_config
            )
            
            # Start batch processing
            print(f"🔄 Starting batch processing...")
            operation = self.client.batch_process_documents(request=batch_request)
            
            # Wait for completion
            print(f"⏳ Waiting for batch processing to complete (timeout: {timeout}s)...")
            operation.result(timeout=timeout)
            
            # Get results
            print(f"📥 Downloading results...")
            # Results are in GCS, need to download and parse
            # The output will be in the output folder
            output_prefix = f"{gcs_prefix}/output/"
            blobs = list(bucket.list_blobs(prefix=output_prefix))
            
            if not blobs:
                raise Exception("No output files found in GCS")
            
            # Download and parse JSON results
            # Batch processing returns results in format:
            # { "responses": [ { "document": {...} } ] }
            for blob in blobs:
                if blob.name.endswith('.json'):
                    json_content = blob.download_as_text()
                    result_data = json.loads(json_content)
                    
                    # Batch processing response structure
                    if 'responses' in result_data and len(result_data['responses']) > 0:
                        # Get the first response's document
                        response = result_data['responses'][0]
                        if 'document' in response:
                            # The document is already a parsed Document object structure
                            # We need to reconstruct it or parse it properly
                            doc_dict = response['document']
                            
                            # Create a mock document object or parse directly
                            # For now, parse the dict structure
                            return {
                                "text": doc_dict.get("text", ""),
                                "pages": self._extract_pages_from_dict(doc_dict.get("pages", [])),
                                "tables": self._extract_tables_from_dict(doc_dict.get("pages", [])),
                                "form_fields": self._extract_form_fields_from_dict(doc_dict.get("entities", [])),
                                "entities": self._extract_entities_from_dict(doc_dict.get("entities", [])),
                                "layout": {},
                                "metadata": {
                                    "page_count": len(doc_dict.get("pages", [])),
                                    "mime_type": doc_dict.get("mimeType", mime_type)
                                }
                            }
            
            raise Exception("Could not find valid output in batch results")
            
        finally:
            # Clean up GCS files
            try:
                blob.delete()
                # Clean up output files
                for output_blob in bucket.list_blobs(prefix=f"{gcs_prefix}/output/"):
                    output_blob.delete()
            except:
                pass
    
    def _parse_document_result(self, document_obj) -> Dict[str, Any]:
        """Parse document result from Document AI response (works with both dict and Document object)."""
        # Handle both dict and Document object
        if hasattr(document_obj, 'text'):
            # It's a Document object
            text = document_obj.text
            pages = document_obj.pages
            entities = document_obj.entities
            mime_type = document_obj.mime_type
        else:
            # It's a dict
            text = document_obj.get("text", "")
            pages = document_obj.get("pages", [])
            entities = document_obj.get("entities", [])
            mime_type = document_obj.get("mimeType", "")
        
        return {
            "text": text,
            "pages": self._extract_pages(pages),
            "tables": self._extract_tables(pages),
            "form_fields": self._extract_form_fields_from_dict(entities),
            "entities": self._extract_entities(entities),
            "layout": self._extract_layout(pages),
            "metadata": {
                "page_count": len(pages) if pages else 0,
                "mime_type": mime_type
            }
        }
    
    def _extract_pages_from_dict(self, pages: list) -> list:
        """Extract page information from document dict."""
        page_data = []
        for i, page in enumerate(pages):
            if hasattr(page, 'page_number'):
                page_num = page.page_number
                dim = page.dimension if hasattr(page, 'dimension') else {}
            else:
                page_num = i + 1
                dim = page.get("dimension", {}) if isinstance(page, dict) else {}
            
            page_data.append({
                "page_number": page_num,
                "dimension": {
                    "width": dim.width if hasattr(dim, 'width') else dim.get("width", 0) if isinstance(dim, dict) else 0,
                    "height": dim.height if hasattr(dim, 'height') else dim.get("height", 0) if isinstance(dim, dict) else 0
                }
            })
        return page_data
    
    def _extract_tables_from_dict(self, pages: list) -> list:
        """Extract tables from pages dict."""
        tables = []
        for page in pages:
            page_tables = page.get("tables", []) if isinstance(page, dict) else (page.tables if hasattr(page, 'tables') else [])
            for table in page_tables:
                tables.append({
                    "page_number": page.get("pageNumber", 1) if isinstance(page, dict) else (page.page_number if hasattr(page, 'page_number') else 1),
                    "rows": []  # Simplified - would need full table parsing
                })
        return tables
    
    def _extract_form_fields_from_dict(self, entities: list) -> dict:
        """Extract form fields from entities dict."""
        form_fields = {}
        for entity in entities:
            if isinstance(entity, dict):
                entity_type = entity.get("type", "")
                if "form_field" in entity_type.lower() or "key_value" in entity_type.lower():
                    form_fields[entity.get("mentionText", "")] = {
                        "value": entity.get("mentionText", ""),
                        "confidence": entity.get("confidence", 0.0)
                    }
        return form_fields
    
    def _extract_entities_from_dict(self, entities: list) -> list:
        """Extract entities from dict."""
        entity_data = []
        for entity in entities:
            if isinstance(entity, dict):
                entity_data.append({
                    "type": entity.get("type", ""),
                    "mention_text": entity.get("mentionText", ""),
                    "confidence": entity.get("confidence", 0.0)
                })
        return entity_data
    
    def process_document(
        self,
        pdf_path: str,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """
        Process a PDF document and extract text, structure, and entities.
        
        Args:
            pdf_path: Path to PDF file
            mime_type: MIME type of the document (default: application/pdf)
        
        Returns:
            Dictionary containing:
            - text: Full extracted text
            - pages: List of page information
            - tables: Extracted tables
            - form_fields: Key-value pairs from forms
            - entities: Extracted entities
            - layout: Document layout information
        """
        if not self.processor_name:
            raise ValueError(
                "Processor not configured. Set processor_id or create default processor."
            )
        
        # Read PDF file
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
        
        # Create raw document
        raw_document = documentai.RawDocument(
            content=pdf_content,
            mime_type=mime_type
        )
        
        # Create process request
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document
        )
        
        # Process document
        result = self.client.process_document(request=request)
        document = result.document
        
        # Extract information
        return {
            "text": document.text,
            "pages": self._extract_pages(document.pages),
            "tables": self._extract_tables(document.pages),
            "form_fields": self._extract_form_fields(document),
            "entities": self._extract_entities(document.entities),
            "layout": self._extract_layout(document.pages),
            "metadata": {
                "page_count": len(document.pages),
                "mime_type": document.mime_type,
                "text_confidence": getattr(document, "text_confidence", None)
            }
        }
    
    def _extract_pages(self, pages: List) -> List[Dict[str, Any]]:
        """Extract page-level information."""
        page_data = []
        for page in pages:
            page_data.append({
                "page_number": page.page_number,
                "dimension": {
                    "width": page.dimension.width,
                    "height": page.dimension.height
                },
                "layout": {
                    "orientation": page.layout.orientation.name if hasattr(page.layout, 'orientation') else None
                }
            })
        return page_data
    
    def _extract_tables(self, pages: List) -> List[Dict[str, Any]]:
        """Extract tables from document pages."""
        tables = []
        for page in pages:
            if hasattr(page, 'tables'):
                for table in page.tables:
                    table_data = {
                        "page_number": page.page_number,
                        "rows": [],
                        "column_count": len(table.header_rows[0].cells) if table.header_rows else 0,
                        "row_count": len(table.body_rows) if hasattr(table, 'body_rows') else 0
                    }
                    
                    # Extract header rows
                    if table.header_rows:
                        for header_row in table.header_rows:
                            row = []
                            for cell in header_row.cells:
                                cell_text = self._get_text_from_layout_element(cell.layout)
                                row.append(cell_text)
                            table_data["rows"].append({"type": "header", "cells": row})
                    
                    # Extract body rows
                    if hasattr(table, 'body_rows'):
                        for body_row in table.body_rows:
                            row = []
                            for cell in body_row.cells:
                                cell_text = self._get_text_from_layout_element(cell.layout)
                                row.append(cell_text)
                            table_data["rows"].append({"type": "body", "cells": row})
                    
                    tables.append(table_data)
        return tables
    
    def _extract_form_fields(self, document) -> Dict[str, Any]:
        """Extract form fields (key-value pairs) from document."""
        form_fields = {}
        if hasattr(document, 'entities'):
            for entity in document.entities:
                if entity.type_ in ["form_field", "key_value_pair"]:
                    # Extract key and value
                    key = None
                    value = None
                    
                    if hasattr(entity, 'properties'):
                        for prop in entity.properties:
                            if prop.type_ == "key":
                                key = prop.mention_text
                            elif prop.type_ == "value":
                                value = prop.mention_text
                    
                    if key:
                        form_fields[key] = {
                            "value": value or entity.mention_text,
                            "confidence": entity.confidence
                        }
        return form_fields
    
    def _extract_entities(self, entities: List) -> List[Dict[str, Any]]:
        """Extract entities from document."""
        entity_data = []
        for entity in entities:
            entity_data.append({
                "type": entity.type_,
                "mention_text": entity.mention_text,
                "confidence": entity.confidence,
                "normalized_value": getattr(entity, 'normalized_value', None)
            })
        return entity_data
    
    def _extract_layout(self, pages: List) -> Dict[str, Any]:
        """Extract layout information from pages."""
        layout_info = {
            "pages": []
        }
        
        for page in pages:
            page_layout = {
                "page_number": page.page_number,
                "blocks": [],
                "paragraphs": [],
                "lines": []
            }
            
            # Extract blocks, paragraphs, lines if available
            if hasattr(page, 'blocks'):
                for block in page.blocks:
                    block_text = self._get_text_from_layout_element(block.layout)
                    page_layout["blocks"].append({
                        "text": block_text,
                        "bounding_box": self._get_bounding_box(block.layout)
                    })
            
            layout_info["pages"].append(page_layout)
        
        return layout_info
    
    def _get_text_from_layout_element(self, layout_element) -> str:
        """Extract text from a layout element."""
        if hasattr(layout_element, 'text_anchor'):
            if layout_element.text_anchor.text_segments:
                # This would need the full document text to extract
                # For now, return empty or use mention_text if available
                return ""
        return getattr(layout_element, 'text', '')
    
    def _get_bounding_box(self, layout_element) -> Optional[Dict[str, float]]:
        """Extract bounding box from layout element."""
        if hasattr(layout_element, 'bounding_poly'):
            vertices = layout_element.bounding_poly.vertices
            if vertices:
                return {
                    "x1": vertices[0].x,
                    "y1": vertices[0].y,
                    "x2": vertices[2].x if len(vertices) > 2 else vertices[0].x,
                    "y2": vertices[2].y if len(vertices) > 2 else vertices[0].y
                }
        return None
    
    def batch_process_documents(
        self,
        pdf_paths: List[str],
        output_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch.
        
        Args:
            pdf_paths: List of paths to PDF files
            output_dir: Optional directory to save results as JSON
        
        Returns:
            List of processing results
        """
        results = []
        for pdf_path in pdf_paths:
            try:
                result = self.process_document(pdf_path)
                results.append({
                    "file": pdf_path,
                    "status": "success",
                    "data": result
                })
                
                # Save to file if output_dir specified
                if output_dir:
                    output_path = Path(output_dir) / f"{Path(pdf_path).stem}.json"
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
            
            except Exception as e:
                results.append({
                    "file": pdf_path,
                    "status": "error",
                    "error": str(e)
                })
        
        return results


# Example usage and configuration helper
def create_service_from_env() -> Optional[DocumentAIService]:
    """
    Create DocumentAIService from environment variables.
    
    Required env vars:
    - GCP_PROJECT_ID
    - DOCUMENT_AI_PROCESSOR_ID (optional)
    - GCP_LOCATION (optional, default: us)
    - GCP_CREDENTIALS_PATH (optional, uses default credentials if not set)
    """
    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id:
        return None
    
    return DocumentAIService(
        project_id=project_id,
        location=os.getenv("GCP_LOCATION", "us"),
        processor_id=os.getenv("DOCUMENT_AI_PROCESSOR_ID"),
        credentials_path=os.getenv("GCP_CREDENTIALS_PATH")
    )
