# Tingathe CV Screening System
React.js (Vite) + Python/FastAPI + SQLAlchemy for recruitment vacancies, document screening, Director review, and reporting.

## Run the UI
```
cd frontend
npm install
npm run dev     # http://localhost:5173
```
Pages: public careers site (`/`), vacancy and apply (`/vacancies/<uuid>`), my applications (`/me`), sign in/register, and the Director workspace (`/admin`). Use the demo sign-in buttons on `/login`.

The vacancy IDs are generated UUIDs, so use the links shown by the application rather than assuming a numeric vacancy URL.

## Demo accounts

The local SQLite seed creates these accounts:

- Director: `william@example.com` / `director123`
- Applicant: `chikondi@example.com` / `applicant123`

## Make it the school's own
- Colours: edit `--brand` and `--accent` at the top of `frontend/src/styles.css`.
- Pictures: replace the files in `frontend/public/images` (keep the names) with real school photos.
- Local seed data: edit `backend/seed.py` if the demo vacancies or accounts need to change.

## Backend (local SQLite)

Python 3.12 or later is recommended. From PowerShell:

```
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Without a `DATABASE_URL` environment variable, the API creates `backend/tingathe.db`, initializes all tables, and seeds local development data. The frontend Vite server proxies `/api` requests to `http://localhost:8000`.

## Backend (PostgreSQL)

For a production-style database, set `DATABASE_URL` before starting the API and apply the PostgreSQL schema:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/tingathe"
psql tingathe -f schema.sql
uvicorn main:app --reload --port 8000
```

The SQLite development seed only runs for SQLite. Use an explicit deployment or migration process to populate PostgreSQL.

## API behavior

- Public users can browse open, non-expired vacancies.
- Applicants register or log in, upload PDF/DOC/DOCX/JPEG/PNG documents, and receive a persisted screening result.
- PDF and DOCX text is extracted automatically; scanned PDFs fall back to OCR when Tesseract is installed.
- Screening scores are weighted and explainable by criterion. Low-confidence extraction is flagged for manual review.
- Directors can create/publish vacancies, review criterion evidence, record shortlist/hold/not-shortlisted decisions, inspect the audit log, and download CSV/PDF reports.
- Uploaded documents are stored under `backend/storage/documents`; protect this directory and configure appropriate retention in production.

## Ideas for later
SMS or WhatsApp status updates, a real Chichewa translation for the language switch, and a read-only link for the school board to view the shortlist.
