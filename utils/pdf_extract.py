"""
PDF -> per-page text extraction.

Uses pdfplumber for the normal (text-layer) case. Falls back to OCR
(pytesseract) for pages that come back empty or near-empty, which
happens for scanned/image-only pages such as the CEG academic calendar.
OCR is optional: if pytesseract/tesseract isn't installed locally, we
just skip those pages and print a warning instead of crashing.
"""
import re

import pdfplumber

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def _clean(text: str) -> str:
    """Light cleanup only -- we deliberately do NOT strip stopwords or
    punctuation (the paper does this, but modern embedding models do
    better on natural language than on stopword-stripped fragments)."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _ocr_page(page) -> str:
    if not OCR_AVAILABLE:
        return ""
    try:
        im = page.to_image(resolution=200).original
        return pytesseract.image_to_string(im)
    except Exception as exc:  # pragma: no cover - best effort fallback
        print(f"    [ocr failed on page {page.page_number}: {exc}]")
        return ""


def extract_pages(pdf_path: str) -> list[dict]:
    """Returns [{'page': int, 'text': str}, ...] for every page with
    usable text. Pages that yield nothing even after OCR are skipped."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if len(text.strip()) < 20:
                ocr_text = _ocr_page(page)
                if ocr_text.strip():
                    text = ocr_text
                elif not OCR_AVAILABLE:
                    print(
                        f"    [page {page.page_number}: no text layer and "
                        f"OCR unavailable -- install tesseract-ocr + "
                        f"pytesseract to include this page]"
                    )
            text = _clean(text)
            if text:
                pages.append({"page": page.page_number, "text": text})
    return pages
