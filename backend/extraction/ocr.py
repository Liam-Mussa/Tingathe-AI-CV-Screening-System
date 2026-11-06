"""OCR for scanned or photographed documents.

Tesseract is an optional dependency: it must be installed on the host machine
and is not available in every environment. Every function here degrades to a
`failed` outcome with an explanation instead of raising, so a missing Tesseract
never takes the API down — the document is simply flagged for manual review.
"""
import shutil
from pathlib import Path

from .documents import ExtractionOutcome


def _tesseract_available() -> bool:
    """True when the `tesseract` binary can be found on PATH."""
    return shutil.which("tesseract") is not None


def _ocr_image(image) -> ExtractionOutcome:
    """Run Tesseract over an already-loaded image."""
    try:
        import pytesseract
        from PIL import Image  # noqa: F401 - pytesseract needs PIL to be importable
    except Exception as exc:  # pragma: no cover - depends on the host machine
        return ExtractionOutcome("ocr", "failed", warnings=[f"OCR libraries unavailable: {exc}"])

    if not _tesseract_available():
        return ExtractionOutcome(
            "ocr", "failed",
            warnings=["Tesseract is not installed on the server; document needs manual review"],
        )

    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except Exception as exc:
        return ExtractionOutcome("ocr", "failed", warnings=[f"OCR failed: {exc}"])

    words = [w for w, conf in zip(data.get("text", []), data.get("conf", [])) if str(w).strip()]
    confidences = []
    for raw in data.get("conf", []):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            confidences.append(value)
    confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    text = " ".join(words)

    if not text.strip():
        return ExtractionOutcome(
            "ocr", "failed", confidence=0.0,
            warnings=["OCR found no readable text in the image"],
        )

    status = "ok" if confidence >= 0.7 else "partial"
    return ExtractionOutcome(
        "ocr", status, text=text, confidence=round(confidence, 3),
        warnings=[] if status == "ok" else ["OCR confidence is low"],
    )


def ocr_image_file(path: Path) -> ExtractionOutcome:
    """OCR a standalone image file (a photo of a CV, for example)."""
    try:
        from PIL import Image

        with Image.open(path) as img:
            image = img.convert("RGB")
    except Exception as exc:
        return ExtractionOutcome("ocr", "failed", warnings=[f"Could not open image: {exc}"])
    return _ocr_image(image)


def ocr_page_image(pdf_path: Path, page_no: int) -> str:
    """Render one PDF page to an image and OCR it. Returns text, never raises."""
    try:
        import pymupdf
    except ImportError:  # pragma: no cover
        import fitz as pymupdf  # type: ignore[no-redef]

    try:
        with pymupdf.open(pdf_path) as doc:
            if page_no < 1 or page_no > len(doc):
                return ""
            page = doc[page_no - 1]
            pixmap = page.get_pixmap(dpi=200)
            image = pixmap.tobytes("png")
    except Exception:
        return ""

    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(image)) as img:
            rgb = img.convert("RGB")
    except Exception:
        return ""

    return _ocr_image(rgb).text
