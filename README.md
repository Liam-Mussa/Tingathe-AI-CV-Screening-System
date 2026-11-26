# Tingathe CV Screening System
React.js (Vite) + Python/FastAPI + SQLAlchemy for recruitment vacancies, document screening, Director review, and reporting.

## Run the UI
Start the backend in a separate terminal first (see the backend instructions below), then run:

```
cd frontend
npm install
npm run dev     # http://localhost:5173
```
Keep both the backend on port 8000 and the frontend on port 5173 running while using the app. A Vite `ECONNREFUSED` proxy error means the backend is not reachable on port 8000.
Pages: public careers site (`/`), vacancy and apply (`/vacancies/<uuid>`), my applications (`/me`), sign in/register, password recovery, and the Director workspace (`/admin`). Sign in using a registered account.

The vacancy IDs are generated UUIDs, so use the links shown by the application rather than assuming a numeric vacancy URL.

## Demo accounts

The local SQLite seed creates these accounts:

- Director: `william@example.com` / `Director123`
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
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Without a `DATABASE_URL` environment variable, the API creates `backend/tingathe.db`, initializes all tables, and seeds local development data. The frontend Vite server proxies `/api` requests to `http://127.0.0.1:8000`.

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

## Password and account security

- Passwords must contain at least 8 characters, one uppercase letter and one number.
- Registration requires password confirmation.
- Login, registration and password-reset forms include a Show/Hide password control so users can verify what they entered.
- Password recovery uses a 30-minute expiring reset token. Configure email delivery before production use.
- The Director account is protected and cannot be deleted through the Users page.

## Screening model configuration

The deterministic, explainable screening model learns subject and skill vocabularies from the synthetic applicant records in `tingathe_demo_dataset.xlsx` and role requirements from `vacancies.csv`. Applicant contact fields are not copied into the trained model. Scoring uses the six fixed criteria in `scoring_criteria.csv` (25%, 25%, 20%, 15%, 10%, 5%); their labels and weights are enforced by the backend and cannot be edited in the vacancy form. The training script rejects changes to the fixed rubric. This dataset has no outcome labels, so it configures a transparent rule-based ranker rather than training a predictive hire/reject classifier.

Vacancy managers can mark fixed criteria as applicable or not applicable per role. The fixed weights are never modified; the score is normalized over only the applicable criteria. Directors can use **Reset & score again** on an application to create a fresh screening run from its saved profile. The admin search covers applicants and vacancies.

Rebuild the configuration with:

```powershell
cd backend
.venv\Scripts\python.exe scoring\train_from_workbook.py
```

This reads the workbook and both CSV files and regenerates `backend/scoring/trained_model.json`, which is loaded by the backend automatically. Imported vacancies include their subject, qualification, experience, skills and district. Applicant applications collect the corresponding profile details in addition to the CV.

## Ideas for later
SMS or WhatsApp status updates, a real Chichewa translation for the language switch, and a read-only link for the school board to view the shortlist.
