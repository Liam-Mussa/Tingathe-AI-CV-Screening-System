"""Document text extraction.

Reads text out of the files applicants upload: PDFs via PyMuPDF, Word documents
via python-docx, and scanned or photographed documents via Tesseract OCR. Each
extractor reports how confident it is, so the screening pipeline can flag a
document for manual review instead of silently scoring an empty CV.
"""
