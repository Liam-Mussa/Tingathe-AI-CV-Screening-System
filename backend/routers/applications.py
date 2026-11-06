"""Application submission, document processing and Director review endpoints."""
from datetime import datetime
from pathlib import Path
import hashlib
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api_helpers import (
    DB,
    application_response,
    audit,
    current_user,
    director_only,
    _parse_uuid,
    validate_upload_size,
)
from config import ALLOWED_CONTENT_TYPES, STORAGE_DIR
from extraction.documents import extract_document
from models import (
    Application,
    CandidateProfile,
    CriterionScore,
    Decision,
    Document,
    ExtractionRun,
    ProfileItem,
    ScreeningResult,
    User,
    Vacancy,
)
from nlp.profile import parse_document
from schemas import ApplicationDecisionRequest, ApplicationResponse
from scoring.engine import score_application

router = APIRouter(prefix="/api/applications", tags=["applications"])

_SUFFIX_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def _safe_filename(name: str | None) -> str:
    raw = Path(name or "document").name
    return re.sub(r"[^A-Za-z0-9_. -]", "_", raw) or "document"


def _content_type(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    return upload.content_type if upload.content_type in ALLOWED_CONTENT_TYPES else _SUFFIX_TYPES.get(suffix, "")


def _find_evidence_item(profile: CandidateProfile, evidence: str):
    if not evidence:
        return None
    target = evidence.strip().lower()
    for item in profile.items:
        if (item.source_snippet or "").strip().lower() == target:
            return item
    for item in profile.items:
        if target in (item.source_snippet or "").lower() or target in item.value.lower():
            return item
    return None


def _get_application(db: Session, application_id: str) -> Application:
    application = db.get(Application, _parse_uuid(application_id))
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def _can_view(application: Application, user: User) -> None:
    if user.role != "director" and application.applicant_id != user.id:
        raise HTTPException(status_code=403, detail="You cannot view this application")


async def _read_upload(upload: UploadFile) -> tuple[bytes, str]:
    content_type = _content_type(upload)
    if not content_type:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {upload.filename or 'unknown'}")
    data = await upload.read()
    validate_upload_size(len(data))
    if not data:
        raise HTTPException(status_code=400, detail=f"{upload.filename or 'Document'} is empty")
    return data, content_type


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def submit_application(
    db: DB,
    user: User = Depends(current_user),
    vacancy_id: str = Form(...),
    phone: str = Form(default=""),
    note: str = Form(default=""),
    files: list[UploadFile] = File(default=[]),
):
    """Submit documents and run the first explainable screening pass."""
    vacancy = db.get(Vacancy, _parse_uuid(vacancy_id))
    if not vacancy or not vacancy.is_open:
        raise HTTPException(status_code=404, detail="Vacancy is not open")
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one CV or qualification document")
    if phone.strip():
        user.phone = phone.strip()

    uploads: list[tuple[UploadFile, bytes, str]] = []
    for upload in files:
        data, content_type = await _read_upload(upload)
        uploads.append((upload, data, content_type))

    if db.query(Application).filter(
        Application.vacancy_id == vacancy.id,
        Application.applicant_id == user.id,
    ).first():
        raise HTTPException(status_code=409, detail="You have already applied for this vacancy")

    application = Application(
        vacancy_id=vacancy.id,
        applicant_id=user.id,
        status="processing",
        cover_note=note.strip() or None,
    )
    db.add(application)
    db.flush()

    application_dir = STORAGE_DIR / str(application.id)
    application_dir.mkdir(parents=True, exist_ok=True)
    extracted_text: list[str] = []
    extraction_needs_review = False

    for index, (upload, data, content_type) in enumerate(uploads):
        original_name = _safe_filename(upload.filename)
        suffix = Path(original_name).suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        storage_path = application_dir / stored_name
        storage_path.write_bytes(data)
        doc = Document(
            application_id=application.id,
            doc_type="cv" if index == 0 else "qualification",
            original_name=original_name,
            storage_path=str(storage_path),
            mime_type=content_type,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )
        db.add(doc)
        db.flush()

        outcome = extract_document(storage_path, content_type, original_name)
        db.add(ExtractionRun(
            document_id=doc.id,
            method=outcome.method,
            status=outcome.status,
            text_content=outcome.text,
            confidence=outcome.confidence,
            warnings=outcome.warnings,
            finished_at=datetime.utcnow(),
        ))
        extracted_text.append(outcome.text)
        extraction_needs_review = extraction_needs_review or outcome.needs_review

    parsed = parse_document("\n\n".join(text for text in extracted_text if text.strip()))
    profile_needs_review = extraction_needs_review or parsed.needs_review
    candidate_profile = CandidateProfile(
        application_id=application.id,
        total_experience_months=parsed.total_experience_months,
        extraction_status="needs_review" if profile_needs_review else "ok",
    )
    db.add(candidate_profile)
    db.flush()

    for item in parsed.items:
        db.add(ProfileItem(
            profile_id=candidate_profile.id,
            item_type=item.item_type,
            value=item.value,
            institution=item.institution,
            source_snippet=item.source_snippet,
            confidence=item.confidence,
            source_document_id=application.documents[0].id if application.documents else None,
        ))
    db.flush()

    score = score_application(parsed, vacancy.criteria)
    result = ScreeningResult(
        application_id=application.id,
        total_score=score.total_score,
        scoring_version=score.scoring_version,
        run_at=datetime.utcnow(),
    )
    db.add(result)
    db.flush()
    criteria_by_id = {str(criterion.id): criterion for criterion in vacancy.criteria}
    for item in score.scores:
        criterion = criteria_by_id.get(item.criterion_id)
        if not criterion:
            continue
        evidence_item = _find_evidence_item(candidate_profile, item.evidence)
        db.add(CriterionScore(
            result_id=result.id,
            criterion_id=criterion.id,
            matched=item.matched,
            score=item.score,
            evidence_item_id=evidence_item.id if evidence_item else None,
            explanation=item.explanation,
        ))

    application.status = "needs_review" if profile_needs_review else "screened"
    audit(db, "Application received", None, "application", str(application.id), {"vacancy": vacancy.title})
    audit(db, "Screening run completed", None, "application", str(application.id), {
        "score": score.total_score,
        "needs_review": profile_needs_review,
    })
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already applied for this vacancy") from None
    db.refresh(application)
    return application_response(application)


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    db: DB,
    vacancy_id: str | None = None,
    user: User = Depends(current_user),
):
    query = db.query(Application).order_by(Application.submitted_at.desc())
    if user.role != "director":
        query = query.filter(Application.applicant_id == user.id)
    if vacancy_id:
        query = query.filter(Application.vacancy_id == _parse_uuid(vacancy_id))
    return [application_response(application) for application in query.all()]


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: str,
    db: DB,
    user: User = Depends(current_user),
):
    application = _get_application(db, application_id)
    _can_view(application, user)
    return application_response(application)


@router.post("/{application_id}/decision", response_model=ApplicationResponse)
def decide_application(
    application_id: str,
    payload: ApplicationDecisionRequest,
    db: DB,
    user: User = Depends(director_only),
):
    application = _get_application(db, application_id)
    decision = Decision(
        application_id=application.id,
        decided_by=user.id,
        decision=payload.decision,
        note=payload.note.strip() if payload.note else None,
    )
    db.add(decision)
    application.status = "decided"
    audit(db, f"Recorded decision: {payload.decision.replace('_', ' ')}", user.id, "application", str(application.id))
    db.commit()
    db.refresh(application)
    return application_response(application)


@router.post("/{application_id}/advance", response_model=ApplicationResponse)
def advance_application(
    application_id: str,
    db: DB,
    user: User = Depends(director_only),
):
    application = _get_application(db, application_id)
    order = ["submitted", "processing", "screened", "decided"]
    if application.status in order and application.status != "decided":
        application.status = order[min(order.index(application.status) + 1, len(order) - 1)]
    audit(db, "Advanced application pipeline", user.id, "application", str(application.id))
    db.commit()
    db.refresh(application)
    return application_response(application)


@router.get("/{application_id}/documents/{document_id}")
def download_document(
    application_id: str,
    document_id: str,
    db: DB,
    user: User = Depends(current_user),
):
    application = _get_application(db, application_id)
    _can_view(application, user)
    document = db.get(Document, _parse_uuid(document_id))
    if not document or document.application_id != application.id:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(document.storage_path).resolve()
    storage_root = STORAGE_DIR.resolve()
    try:
        path.relative_to(storage_root)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document file is missing")
    return FileResponse(path, media_type=document.mime_type, filename=document.original_name)
