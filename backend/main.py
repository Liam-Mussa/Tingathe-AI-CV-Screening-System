"""Tingathe CV Screening API entry point.

Run from this directory with:
    .venv\\Scripts\\python.exe -m uvicorn main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import DATABASE_URL, settings
from database import SessionLocal, init_db
from routers import applications, audit, auth, notifications, reports, vacancies
from seed import seed_development_data


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # Seed only the local SQLite database. Production PostgreSQL should be
    # populated through an explicit deployment/migration step.
    if DATABASE_URL.startswith("sqlite"):
        with SessionLocal() as db:
            seed_development_data(db)
    yield


app = FastAPI(title="Tingathe CV Screening API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.1.111:5173",
        "http://192.168.1.100:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}):5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vacancies.router)
app.include_router(applications.router)
app.include_router(audit.router)
app.include_router(reports.router)
app.include_router(notifications.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "database": "sqlite" if DATABASE_URL.startswith("sqlite") else "postgresql",
        "settings": settings(),
    }
