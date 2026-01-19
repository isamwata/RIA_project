# Document Folder Structure

This project uses an organized folder structure to separate RIA documents from EU Impact Assessment documents.

## Folder Structure

```
RIA_pdf/          # Source RIA PDF documents (Belgian Federal RIAs)
RIA_txt/          # Processed RIA text outputs (extracted from PDFs)

EU_pdf/           # Source EU Impact Assessment PDF documents
EU_txt/           # Processed EU Impact Assessment text outputs
```

## Usage

### Processing PDFs

The `process_pdf_with_document_ai.py` script automatically organizes files:

```bash
# Process a PDF from RIA_pdf folder
python process_pdf_with_document_ai.py RIA_pdf/document.pdf
# Output saved to: RIA_txt/document.txt

# Process a PDF from EU_pdf folder
python process_pdf_with_document_ai.py EU_pdf/document.pdf
# Output saved to: EU_txt/document.txt
```

### Organizing Existing Files

To organize existing PDF and TXT files into the proper folders:

```bash
python organize_documents.py
```

This script will:
- Move PDFs to `RIA_pdf/` or `EU_pdf/` based on filename patterns
- Move TXT files to `RIA_txt/` or `EU_txt/` accordingly
- Skip files that are already in the correct location

## File Detection

The system automatically detects document type based on:

1. **Folder location**: Files in `RIA_pdf/` or `EU_pdf/` are automatically categorized
2. **Filename patterns**: Files with keywords like "EU", "European", "SWD", "Impact Assessment" are treated as EU documents
3. **Default**: If unclear, files are treated as RIA documents

## Current Status

Run `organize_documents.py` to see current file counts in each folder.

## Best Practices

1. **Place source PDFs** in the appropriate `*_pdf/` folder
2. **Process PDFs** using `process_pdf_with_document_ai.py`
3. **Outputs are automatically saved** to the corresponding `*_txt/` folder
4. **Keep source and processed files** organized in their respective folders
