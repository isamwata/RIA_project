#!/usr/bin/env python3
"""Extract text from Word document and analyze structure."""

from docx import Document
import sys

def read_docx(file_path):
    """Read Word document and extract all text."""
    doc = Document(file_path)
    
    text_content = []
    for para in doc.paragraphs:
        if para.text.strip():
            text_content.append(para.text)
    
    return '\n'.join(text_content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python read_docx.py <docx_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    content = read_docx(file_path)
    
    # Write to text file
    output_file = file_path.replace('.docx', '.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Extracted text saved to: {output_file}")
    print(f"\nTotal paragraphs: {len(content.split(chr(10)))}\n")
    print("First 2000 characters:")
    print(content[:2000])
