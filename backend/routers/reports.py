"""CSV and PDF report generation."""
from csv import writer
from io import BytesIO, StringIO
from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from api_helpers import DB, director_only, _parse_uuid
from models import Application, User, Vacancy

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-").lower() or "report"


def _vacancy(db, vacancy_id: str) -> Vacancy:
    vacancy = db.get(Vacancy, _parse_uuid(vacancy_id))
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy


def _applications(db, vacancy_id: str):
    return (
        db.query(Application)
        .filter(Application.vacancy_id == _parse_uuid(vacancy_id))
        .all()
    )


def _decision(application: Application) -> str:
    latest = max(application.decisions, key=lambda item: item.decided_at, default=None)
    if not latest:
        return "Undecided"
    return {
        "shortlist": "Shortlisted",
        "hold": "Hold",
        "not_shortlisted": "Not shortlisted",
    }.get(latest.decision, latest.decision)


def _score(application: Application):
    result = max(application.results, key=lambda item: item.run_at, default=None)
    return float(result.total_score) if result else None


@router.get("/csv")
def csv_report(
    db: DB,
    vacancy_id: str = Query(...),
    user: User = Depends(director_only),
):
    vacancy = _vacancy(db, vacancy_id)
    applications = sorted(_applications(db, vacancy_id), key=lambda app: _score(app) or -1, reverse=True)
    output = StringIO()
    csv = writer(output)
    csv.writerow(["Rank", "Applicant", "Email", "Phone", "Score", "Decision", "Status", "Submitted"])
    for rank, application in enumerate(applications, start=1):
        csv.writerow([
            rank,
            application.applicant.full_name,
            application.applicant.email,
            application.applicant.phone or "",
            _score(application) if _score(application) is not None else "Not scored",
            _decision(application),
            application.status,
            application.submitted_at.isoformat() if application.submitted_at else "",
        ])
    filename = f"{_safe_name(vacancy.title)}-applicants.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf")
def pdf_report(
    db: DB,
    vacancy_id: str = Query(...),
    user: User = Depends(director_only),
):
    vacancy = _vacancy(db, vacancy_id)
    applications = sorted(_applications(db, vacancy_id), key=lambda app: _score(app) or -1, reverse=True)
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Tingathe recruitment report: {vacancy.title}", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"{len(applications)} application(s) · generated for Director review", styles["Normal"]),
        Spacer(1, 18),
    ]
    rows = [["Rank", "Applicant", "Score", "Decision", "Status"]]
    for rank, application in enumerate(applications, start=1):
        rows.append([
            str(rank),
            application.applicant.full_name,
            str(_score(application)) if _score(application) is not None else "Not scored",
            _decision(application),
            application.status,
        ])
    table = Table(rows, repeatRows=1, colWidths=[42, 190, 70, 105, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17305C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5DAE5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    document.build(story)
    filename = f"{_safe_name(vacancy.title)}-report.pdf"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
