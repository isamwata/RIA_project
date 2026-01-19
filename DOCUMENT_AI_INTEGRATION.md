# Document AI Integration for RIA Project

## Overview

Google Cloud Document AI is a powerful document understanding platform that can significantly enhance PDF extraction capabilities for the RIA automation project. This document outlines how Document AI can be integrated and its advantages over the current PyMuPDF + Tesseract OCR approach.

## Current Implementation

The project currently uses:
- **PyMuPDF (fitz)**: For extracting selectable text from PDFs
- **Tesseract OCR**: For extracting text from embedded images
- **PIL/Pillow**: For image processing

**Limitations of Current Approach:**
- OCR accuracy depends on Tesseract's capabilities
- Limited structured data extraction (tables, forms, key-value pairs)
- No understanding of document layout or semantic structure
- Manual handling of complex document formats
- No native support for form parsing or entity extraction

## What is Document AI?

Google Cloud Document AI is a unified platform for document understanding that provides:

1. **OCR (Optical Character Recognition)**: High-accuracy text extraction
2. **Form Parser**: Extract key-value pairs from forms
3. **Invoice Parser**: Specialized invoice processing
4. **Identity Document Parser**: ID card/passport extraction
5. **Custom Processors**: Train custom models for specific document types
6. **Layout Analysis**: Understand document structure (tables, paragraphs, headers)
7. **Entity Extraction**: Identify and extract structured entities

## Benefits for RIA Project

### 1. **Superior OCR Accuracy**
- Document AI uses Google's advanced ML models
- Better handling of:
  - Scanned documents
  - Poor quality images
  - Multi-column layouts
  - Complex fonts and languages
  - Handwritten text (with specialized processors)

### 2. **Structured Data Extraction**
RIA documents often contain:
- **Tables**: Impact assessment tables, administrative burden matrices
- **Forms**: Standardized RIA templates with checkboxes and fields
- **Key-Value Pairs**: Author information, contact details, proposal metadata

Document AI can extract these as structured JSON, making downstream processing easier.

### 3. **Layout Understanding**
- Identifies document sections (headers, paragraphs, tables, lists)
- Preserves hierarchical structure
- Understands reading order
- Better handling of multi-column layouts

### 4. **Custom Processors for RIA Documents**
You can train custom Document AI processors specifically for:
- Belgian RIA template structure
- EU Impact Assessment format
- 21-theme impact assessment tables
- Administrative burden forms

### 5. **Entity Extraction**
Automatically identify and extract:
- Proposal titles
- Author names and contact information
- Dates and deadlines
- Impact categories
- Target groups (SMEs, citizens, enterprises)
- References to other documents

### 6. **Batch Processing**
- Process multiple documents in parallel
- Efficient for handling multiple RIA proposals
- Built-in retry logic and error handling

## Integration Architecture

### Option 1: Hybrid Approach (Recommended)

Keep current `pdf_reader.py` as fallback, add Document AI as primary:

```
┌─────────────────────────────────────────┐
│         Document Ingestion              │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌──────────────┐  ┌──────────────┐
│ Document AI  │  │ PyMuPDF +    │
│ (Primary)    │  │ Tesseract    │
│              │  │ (Fallback)   │
└──────┬───────┘  └──────┬───────┘
       │                 │
       └────────┬────────┘
                │
       ┌────────▼────────┐
       │  Unified Output  │
       │  (Structured)    │
       └────────┬─────────┘
                │
       ┌────────▼────────┐
       │  Vector DB      │
       │  Knowledge Base │
       └─────────────────┘
```

### Option 2: Document AI Only

Replace current implementation entirely with Document AI for all PDF processing.

## Implementation Strategy

### Phase 1: Basic Integration

1. **Set up Google Cloud Project**
   - Enable Document AI API
   - Create service account
   - Generate credentials JSON

2. **Install Dependencies**
   ```bash
   pip install google-cloud-documentai
   ```

3. **Create Document AI Service**
   ```python
   # backend/document_ai_service.py
   from google.cloud import documentai
   from google.oauth2 import service_account
   
   class DocumentAIService:
       def __init__(self, credentials_path: str, processor_id: str):
           # Initialize client
           pass
       
       def process_document(self, pdf_path: str) -> dict:
           # Extract text, layout, entities
           pass
       
       def extract_tables(self, document: dict) -> list:
           # Extract structured tables
           pass
       
       def extract_form_fields(self, document: dict) -> dict:
           # Extract key-value pairs
           pass
   ```

4. **Update PDF Reader**
   - Add Document AI as primary extraction method
   - Keep PyMuPDF/Tesseract as fallback
   - Unify output format

### Phase 2: Custom Processor Training

1. **Prepare Training Data**
   - Collect sample RIA documents (Belgian + EU)
   - Label key sections and fields
   - Create training dataset

2. **Train Custom Processor**
   - Use Document AI Custom Extractor
   - Train on RIA-specific structure
   - Validate on test set

3. **Deploy Custom Processor**
   - Deploy to production
   - Update service to use custom processor

### Phase 3: Advanced Features

1. **Entity Extraction**
   - Extract proposal metadata automatically
   - Identify impact categories
   - Extract target groups

2. **Table Extraction**
   - Extract 21-theme assessment tables
   - Extract administrative burden matrices
   - Convert to structured JSON

3. **Form Parsing**
   - Parse RIA template forms
   - Extract checkboxes and fields
   - Validate completeness

## Code Example: Document AI Integration

### Basic Text Extraction

```python
from google.cloud import documentai
from google.oauth2 import service_account
import io

class DocumentAIService:
    def __init__(self, project_id: str, location: str, 
                 processor_id: str, credentials_path: str):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        self.client = documentai.DocumentProcessorServiceClient(
            credentials=credentials
        )
        self.name = self.client.processor_path(
            project_id, location, processor_id
        )
    
    def extract_text(self, pdf_path: str) -> dict:
        """Extract text and structure from PDF."""
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
        
        raw_document = documentai.RawDocument(
            content=pdf_content, mime_type="application/pdf"
        )
        
        request = documentai.ProcessRequest(
            name=self.name, raw_document=raw_document
        )
        
        result = self.client.process_document(request=request)
        document = result.document
        
        return {
            "text": document.text,
            "pages": [
                {
                    "page_number": page.page_number,
                    "text": page.layout.text_anchor.text_segments,
                    "dimension": {
                        "width": page.dimension.width,
                        "height": page.dimension.height
                    }
                }
                for page in document.pages
            ],
            "entities": [
                {
                    "type": entity.type_,
                    "mention_text": entity.mention_text,
                    "confidence": entity.confidence
                }
                for entity in document.entities
            ]
        }
    
    def extract_tables(self, document: dict) -> list:
        """Extract tables from document."""
        tables = []
        for page in document["pages"]:
            # Document AI provides table structure
            # Extract rows, columns, cells
            pass
        return tables
```

### Integration with Current System

```python
# backend/pdf_extractor.py (updated)
from pathlib import Path
from typing import Optional
import os

from .document_ai_service import DocumentAIService
from pdf_reader import process_pdf  # Current implementation

class PDFExtractor:
    def __init__(self, use_document_ai: bool = True):
        self.use_document_ai = use_document_ai
        if use_document_ai:
            self.doc_ai_service = DocumentAIService(
                project_id=os.getenv("GCP_PROJECT_ID"),
                location=os.getenv("GCP_LOCATION", "us"),
                processor_id=os.getenv("DOCUMENT_AI_PROCESSOR_ID"),
                credentials_path=os.getenv("GCP_CREDENTIALS_PATH")
            )
    
    def extract(self, pdf_path: Path) -> dict:
        """Extract text and structure from PDF."""
        if self.use_document_ai:
            try:
                return self._extract_with_document_ai(pdf_path)
            except Exception as e:
                print(f"Document AI failed: {e}, falling back to PyMuPDF")
                return self._extract_with_pymupdf(pdf_path)
        else:
            return self._extract_with_pymupdf(pdf_path)
    
    def _extract_with_document_ai(self, pdf_path: Path) -> dict:
        """Extract using Document AI."""
        result = self.doc_ai_service.extract_text(str(pdf_path))
        return {
            "method": "document_ai",
            "text": result["text"],
            "pages": result["pages"],
            "entities": result["entities"],
            "tables": self.doc_ai_service.extract_tables(result)
        }
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> dict:
        """Fallback to current PyMuPDF implementation."""
        output_path = pdf_path.with_suffix(".txt")
        process_pdf(pdf_path, output_path)
        text = output_path.read_text()
        return {
            "method": "pymupdf_tesseract",
            "text": text,
            "pages": self._parse_pymupdf_output(text)
        }
```

## Configuration

### Environment Variables

Add to `.env`:
```bash
# Google Cloud Document AI
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=your-processor-id
GCP_CREDENTIALS_PATH=./credentials/service-account.json

# Feature flags
USE_DOCUMENT_AI=true
DOCUMENT_AI_FALLBACK=true  # Fallback to PyMuPDF if Document AI fails
```

### Cost Considerations

**Document AI Pricing** (as of 2024):
- OCR: ~$1.50 per 1,000 pages
- Form Parser: ~$1.50 per 1,000 pages
- Custom Processors: Training + usage costs

**Cost Optimization:**
- Use Document AI for complex documents
- Use PyMuPDF for simple text-based PDFs
- Batch process multiple documents
- Cache results to avoid reprocessing

## Use Cases in RIA Project

### 1. Proposal Document Ingestion

**Current**: Manual text extraction, may miss structure
**With Document AI**: 
- Extract proposal metadata (title, author, dates)
- Identify document sections
- Extract references to other documents
- Better handling of multi-language documents

### 2. Historical RIA Processing

**Current**: Basic text extraction
**With Document AI**:
- Extract structured data from 21-theme assessments
- Parse administrative burden tables
- Extract impact classifications (positive/negative/no impact)
- Build structured knowledge base

### 3. EU Impact Assessment Processing

**Current**: OCR may miss complex layouts
**With Document AI**:
- Better extraction of domain-specific sections
- Table extraction for impact matrices
- Entity extraction for policy domains
- Structured data for knowledge graph

### 4. Form-Based RIA Templates

**Current**: Text extraction only
**With Document AI**:
- Parse form fields and checkboxes
- Extract key-value pairs
- Validate form completeness
- Auto-populate structured data

## Integration with Knowledge Base

Document AI output can directly feed into:

1. **Vector Database**:
   - Use extracted text for embeddings
   - Better quality text = better embeddings
   - Include structured metadata

2. **Knowledge Graph**:
   - Entities become nodes
   - Relationships from document structure
   - Tables become structured relationships

3. **LLM Council Context**:
   - Provide structured context to LLMs
   - Better understanding of document structure
   - More accurate impact assessments

## Migration Path

### Step 1: Add Document AI Service (Non-Breaking)
- Add Document AI as optional service
- Keep current implementation
- Feature flag to enable/disable

### Step 2: Parallel Processing
- Process same documents with both methods
- Compare results
- Validate Document AI accuracy

### Step 3: Gradual Migration
- Use Document AI for new documents
- Keep PyMuPDF for existing processed documents
- Migrate historical documents as needed

### Step 4: Custom Processor Training
- Collect RIA-specific training data
- Train custom processor
- Deploy and validate

## Recommendations

1. **Start with Hybrid Approach**: Keep PyMuPDF as fallback
2. **Use Document AI for Complex Documents**: Scanned PDFs, forms, tables
3. **Train Custom Processor**: For RIA-specific structure
4. **Monitor Costs**: Track usage and optimize
5. **Cache Results**: Avoid reprocessing same documents
6. **Batch Processing**: Process multiple proposals efficiently

## Next Steps

1. **Set up Google Cloud Project**
   - Create project
   - Enable Document AI API
   - Create service account

2. **Implement Basic Integration**
   - Add Document AI service
   - Update PDF extractor
   - Test with sample RIA documents

3. **Evaluate Results**
   - Compare with current implementation
   - Measure accuracy improvements
   - Assess cost impact

4. **Plan Custom Processor**
   - Collect training data
   - Design processor schema
   - Plan training pipeline

## References

- [Google Cloud Document AI Documentation](https://cloud.google.com/document-ai/docs)
- [Document AI Python Client](https://cloud.google.com/python/docs/reference/documentai/latest)
- [Custom Processor Training](https://cloud.google.com/document-ai/docs/custom-processor)
- [Pricing Information](https://cloud.google.com/document-ai/pricing)
