"""Runtime configuration, read from the environment so nothing secret is hard-coded."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# PostgreSQL is the production target. Local development defaults to SQLite so
# the API can be started immediately without installing a database server;
# override DATABASE_URL with a PostgreSQL DSN in deployment.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(BASE_DIR / 'tingathe.db').as_posix()}",
)

# Uploaded documents live outside the database and are referenced by path.
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage" / "documents"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Limits, so a malicious upload cannot exhaust the disk.
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
ALLOWED_CONTENT_TYPES = {
    "application/pdf": "cv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "cv",
    "application/msword": "cv",
    "image/jpeg": "other",
    "image/png": "other",
}

# Token signing. In production set SECRET_KEY to a long random value.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-secret-change-me")
TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "72"))

# Which NLP/ML extras are actually available. The scoring pipeline degrades
# gracefully when an optional dependency or model is missing, so the server
# still runs on a machine without spaCy or Tesseract installed.
try:
    import spacy  # noqa: F401

    SPACY_AVAILABLE = True
except Exception:  # pragma: no cover - depends on the host machine
    SPACY_AVAILABLE = False

try:
    import sentence_transformers  # noqa: F401

    EMBEDDINGS_AVAILABLE = True
except Exception:  # pragma: no cover - depends on the host machine
    EMBEDDINGS_AVAILABLE = False

OCR_AVAILABLE = None  # probed lazily in extraction/ocr.py


def settings() -> dict:
    """A small, JSON-friendly summary used by the /api/health endpoint."""
    return {
        "spacy": SPACY_AVAILABLE,
        "embeddings": EMBEDDINGS_AVAILABLE,
        "ocr": bool(OCR_AVAILABLE),
    }
