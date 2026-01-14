"""
pdf_reader.py

Extracts text from PDFs that contain selectable text and also runs OCR on
embedded images, keeping per-page structure for references.

Dependencies:
  - pymupdf (install as: pip install pymupdf)
  - pytesseract (pip install pytesseract) and the Tesseract binary installed on the system
  - Pillow (pip install Pillow)

Usage (example):
  python pdf_reader.py input.pdf output.txt
"""

import sys
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io


def extract_page_text(doc: fitz.Document, page_index: int) -> str:
    """Extract selectable text from a page."""
    page = doc.load_page(page_index)
    return page.get_text("text")


def extract_images_simple(doc: fitz.Document, page_index: int) -> List[Tuple[str, Image.Image]]:
    """
    Simplified image extraction that opens the image bytes via PIL directly.
    """
    page = doc.load_page(page_index)
    out: List[Tuple[str, Image.Image]] = []
    for img_index, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        base = doc.extract_image(xref)
        image_bytes = base["image"]
        pil_img = Image.open(io.BytesIO(image_bytes))
        label = f"page_{page_index + 1}_img_{img_index + 1}"
        out.append((label, pil_img))
    return out


def ocr_images(images: List[Tuple[str, Image.Image]]) -> List[Tuple[str, str]]:
    """Run OCR on a list of (label, PIL.Image) and return (label, text)."""
    results: List[Tuple[str, str]] = []
    for label, img in images:
        text = pytesseract.image_to_string(img)
        if text.strip():
            results.append((label, text))
    return results


def process_pdf(input_path: Path, output_path: Path) -> None:
    doc = fitz.open(input_path)

    parts: List[str] = []

    for page_index in range(len(doc)):
        page_number = page_index + 1
        # Extract selectable text
        page_text = extract_page_text(doc, page_index).strip()
        parts.append(f"\n=== Page {page_number} (selectable text) ===\n{page_text}")

        # Extract images and OCR them
        images = extract_images_simple(doc, page_index)
        ocr_results = ocr_images(images)
        if ocr_results:
            parts.append(f"\n=== Page {page_number} (OCR from images) ===")
            for label, text in ocr_results:
                parts.append(f"\n[{label}]\n{text.strip()}")

    output_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python pdf_reader.py input.pdf output.txt")
        sys.exit(1)

    input_pdf = Path(sys.argv[1]).expanduser().resolve()
    output_txt = Path(sys.argv[2]).expanduser().resolve()

    if not input_pdf.exists():
        print(f"Input file not found: {input_pdf}")
        sys.exit(1)

    process_pdf(input_pdf, output_txt)
    print(f"Extraction complete. Output saved to: {output_txt}")


if __name__ == "__main__":
    main()
