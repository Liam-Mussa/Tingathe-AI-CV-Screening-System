"""Text extraction from PDF and Word documents.

Both extractors return an `ExtractionOutcome` describing what happened, so the
caller can store the run and decide whether the document needs manual review.
Nothing here raises for an unreadable file: a failure is data, not an error.
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractionOutcome:
    """The result of trying to read one document."""

    method: str                       # pdf_text | docx | ocr
    status: str                       # ok | partial | failed
    text: str = ""
    confidence: float = 0.0           # 0..1
    warnings: list = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        """True when a human should look at the document before trusting it.

        A short CV is fine — this flags documents we could not read at all, or
        read with low confidence, not documents that happen to be brief.
        """
        return self.status != "ok" or self.confidence < 0.7 or not self.text.strip()


def _confidence(text: str, page_count: int, empty_pages: int) -> float:
    """How confident we are that the text was read correctly (not how long it is).

    Native text extraction is reliable, so it starts high. Confidence drops when
    a page produced almost no text, which is the signature of a scanned or
    image-only page that the text layer could not read.
    """
    if page_count <= 0 or not text.strip():
        return 0.0
    empty_ratio = empty_pages / page_count
    return round(max(0.0, min(1.0, 0.98 - empty_ratio * 0.45)), 3)


def extract_pdf(path: Path) -> ExtractionOutcome:
    """Read a PDF with PyMuPDF, falling back to OCR when a page has no text."""
    try:
        import pymupdf  # PyMuPDF 2.x exposes the module as `pymupdf`
    except ImportError:  # pragma: no cover - depends on the host machine
        import fitz as pymupdf  # type: ignore[no-redef]

    warnings: list = []
    try:
        with pymupdf.open(path) as doc:
            pages = [page.get_text("text") or "" for page in doc]
    except Exception as exc:  # corrupt or unreadable file
        return ExtractionOutcome("pdf_text", "failed", warnings=[f"Could not open PDF: {exc}"])

    text = "\n".join(pages)
    empty_before_ocr = [i for i, p in enumerate(pages, start=1) if len(p.strip()) < 20]

    # A scanned CV has pages with almost no text. Try OCR on those pages.
    if empty_before_ocr and pages:
        from .ocr import ocr_page_image

        recovered = 0
        for page_no in empty_before_ocr:
            try:
                ocr_text = ocr_page_image(path, page_no)
            except Exception as exc:
                warnings.append(f"OCR failed on page {page_no}: {exc}")
                continue
            if ocr_text.strip():
                pages[page_no - 1] = ocr_text
                recovered += 1
        if recovered:
            text = "\n".join(pages)
            warnings.append(f"OCR recovered {recovered} scanned page(s)")

    if not text.strip():
        return ExtractionOutcome(
            "pdf_text", "failed", text="",
            confidence=0.0,
            warnings=warnings + ["No text found in the PDF"],
        )

    still_empty = sum(1 for p in pages if len(p.strip()) < 20)
    confidence = _confidence(text, len(pages), still_empty)
    status = "ok"
    if still_empty:
        status = "partial"
        warnings.append(f"{still_empty} page(s) could not be read as text")
    return ExtractionOutcome("pdf_text", status, text=text, confidence=confidence, warnings=warnings)


def extract_docx(path: Path) -> ExtractionOutcome:
    """Read a Word document, including text inside tables."""
    warnings: list = []
    try:
        import docx  # python-docx

        document = docx.Document(str(path))
    except Exception as exc:
        return ExtractionOutcome("docx", "failed", warnings=[f"Could not open Word file: {exc}"])

    chunks = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                chunks.append(" | ".join(cells))

    text = "\n".join(chunks)
    if not text.strip():
        return ExtractionOutcome(
            "docx", "failed", text="",
            confidence=0.0,
            warnings=["No text found in the Word file"],
        )

    confidence = _confidence(text, 1, 0)
    return ExtractionOutcome("docx", "ok", text=text, confidence=confidence, warnings=warnings)


def extract_document(path: Path, content_type: str, original_name: str) -> ExtractionOutcome:
    """Pick the right extractor for an uploaded file."""
    suffix = path.suffix.lower()
    name = (original_name or path.name).lower()

    if content_type == "application/pdf" or suffix == ".pdf":
        return extract_pdf(path)
    if suffix in {".docx", ".doc"} or content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        return extract_docx(path)
    if suffix in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}:
        # A photo of a CV: OCR is the only way to read it.
        from .ocr import ocr_image_file

        return ocr_image_file(path)

    return ExtractionOutcome(
        "pdf_text", "failed",
        warnings=[f"Unsupported file type: {suffix or name}"],
    )
