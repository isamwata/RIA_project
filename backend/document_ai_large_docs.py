"""
Document AI Service for Large Documents

Handles documents exceeding the 30-page limit by splitting PDFs into chunks
and processing each chunk with Document AI, then combining results.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF

try:
    from google.cloud import documentai
    from google.oauth2 import service_account
    DOCUMENT_AI_AVAILABLE = True
except ImportError:
    DOCUMENT_AI_AVAILABLE = False

from .document_ai_service import DocumentAIService

# Document AI page limit for OCR Processor
PAGE_LIMIT = 30


class LargeDocumentAIService(DocumentAIService):
    """
    Extended Document AI service that handles large documents by splitting them.
    """
    
    def process_large_document(
        self,
        pdf_path: str,
        pages_per_chunk: int = PAGE_LIMIT,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """
        Process a large PDF by splitting it into chunks and processing each.
        
        Args:
            pdf_path: Path to PDF file
            pages_per_chunk: Number of pages per chunk (default: 30, Document AI limit)
            mime_type: MIME type of the document
        
        Returns:
            Combined result from all chunks
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Open PDF to get page count
        pdf_doc = fitz.open(pdf_path)
        total_pages = len(pdf_doc)
        pdf_doc.close()
        
        print(f"📄 Document has {total_pages} pages")
        
        if total_pages <= pages_per_chunk:
            # Small enough to process directly
            print("✅ Document is within page limit, processing directly...")
            return self.process_document(str(pdf_path), mime_type)
        
        # Need to split into chunks
        num_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
        print(f"📦 Splitting into {num_chunks} chunk(s) of up to {pages_per_chunk} pages each...")
        
        all_text_parts = []
        all_pages = []
        all_tables = []
        all_form_fields = {}
        all_entities = []
        all_layout = {"pages": []}
        
        # Process each chunk
        for chunk_num in range(num_chunks):
            start_page = chunk_num * pages_per_chunk
            end_page = min(start_page + pages_per_chunk, total_pages)
            
            print(f"   Processing chunk {chunk_num + 1}/{num_chunks} (pages {start_page + 1}-{end_page})...")
            
            # Create temporary chunk PDF
            chunk_path = pdf_path.parent / f"{pdf_path.stem}_chunk_{chunk_num + 1}.pdf"
            
            try:
                # Extract chunk pages
                pdf_doc = fitz.open(pdf_path)
                chunk_doc = fitz.open()
                chunk_doc.insert_pdf(pdf_doc, from_page=start_page, to_page=end_page - 1)
                chunk_doc.save(str(chunk_path))
                chunk_doc.close()
                pdf_doc.close()
                
                # Process chunk with Document AI
                chunk_result = self.process_document(str(chunk_path), mime_type)
                
                # Combine results
                all_text_parts.append(chunk_result["text"])
                
                # Adjust page numbers in pages data
                for page_data in chunk_result["pages"]:
                    page_data["page_number"] = start_page + page_data.get("page_number", 1)
                    all_pages.append(page_data)
                
                # Combine tables (adjust page numbers)
                for table in chunk_result["tables"]:
                    table["page_number"] = start_page + table.get("page_number", 1)
                    all_tables.append(table)
                
                # Combine form fields
                all_form_fields.update(chunk_result["form_fields"])
                
                # Combine entities
                all_entities.extend(chunk_result["entities"])
                
                # Combine layout
                for page_layout in chunk_result["layout"].get("pages", []):
                    page_layout["page_number"] = start_page + page_layout.get("page_number", 1)
                    all_layout["pages"].append(page_layout)
                
                print(f"   ✅ Chunk {chunk_num + 1} processed ({len(chunk_result['text']):,} chars)")
                
            except Exception as e:
                print(f"   ❌ Error processing chunk {chunk_num + 1}: {e}")
                raise
            finally:
                # Clean up temporary chunk file
                if chunk_path.exists():
                    chunk_path.unlink()
        
        # Combine all text
        combined_text = "\n\n".join(all_text_parts)
        
        print(f"✅ All chunks processed!")
        print(f"   Total text: {len(combined_text):,} characters")
        
        return {
            "text": combined_text,
            "pages": all_pages,
            "tables": all_tables,
            "form_fields": all_form_fields,
            "entities": all_entities,
            "layout": all_layout,
            "metadata": {
                "page_count": total_pages,
                "mime_type": mime_type,
                "chunks_processed": num_chunks,
                "pages_per_chunk": pages_per_chunk
            }
        }
