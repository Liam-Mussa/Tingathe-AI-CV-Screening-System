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
    ApplicantProfile,
    Application,
    CandidateProfile,
    CriterionScore,
    Decision,
    Document,
    ExtractionRun,
    Notification,
    ProfileItem,
    ScreeningResult,
    User,
    Vacancy,
)
from nlp.profile import ProfileItemData, parse_document
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


def _add_form_profile_item(parsed, item_type: str, label: str, value: str, institution=None):
    value = value.strip()
    if value:
        parsed.items.append(ProfileItemData(
            item_type=item_type,
            value=value[:300],
            institution=institution[:200] if institution else None,
            source_snippet=f"Application form: {label}: {value}",
            confidence=1.0,
        ))


def _append_application_details(parsed, details: dict[str, str]) -> None:
    qualification = details["highest_qualification"]
    if qualification:
        _add_form_profile_item(
            parsed,
            "qualification",
            "Highest qualification",
            qualification,
            details["institution"] or None,
        )
    if details["graduation_year"]:
        _add_form_profile_item(
            parsed, "detail", "Graduation year", details["graduation_year"]
        )
    if details["teaching_subject_specialization"]:
        _add_form_profile_item(
            parsed,
            "skill",
            "Teaching subject specialization",
            details["teaching_subject_specialization"],
        )
    if details["professional_teaching_qualification_or_training"]:
        _add_form_profile_item(
            parsed,
            "qualification",
            "Professional teaching qualification or training",
            details["professional_teaching_qualification_or_training"],
        )

    for label in (
        "teaching_methods_and_competencies",
        "subject_specific_skills",
        "additional_skills",
    ):
        for value in re.split(r"[;,\n]+", details[label]):
            _add_form_profile_item(parsed, "skill", label.replace("_", " "), value)

    if details["teaching_experience_summary"]:
        _add_form_profile_item(
            parsed,
            "experience",
            "Teaching experience summary",
            details["teaching_experience_summary"],
        )
    for label in ("most_recent_school", "employment_status"):
        if details[label]:
            _add_form_profile_item(
                parsed, "detail", label.replace("_", " "), details[label]
            )

    years = details["years_secondary_teaching_experience"]
    if years:
        try:
            months = round(float(years) * 12)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Teaching experience must be a non-negative number of years",
            ) from None
        if months < 0 or months > 60 * 12:
            raise HTTPException(
                status_code=422,
                detail="Teaching experience must be between 0 and 60 years",
            )
        parsed.total_experience_months = max(
            parsed.total_experience_months or 0, months
        )


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
    full_name: str = Form(default=""),
    phone: str = Form(default=""),
    district: str = Form(default=""),
    note: str = Form(default=""),
    highest_qualification: str = Form(default=""),
    institution: str = Form(default=""),
    graduation_year: str = Form(default=""),
    teaching_subject_specialization: str = Form(default=""),
    years_secondary_teaching_experience: str = Form(default=""),
    teaching_experience_summary: str = Form(default=""),
    professional_teaching_qualification_or_training: str = Form(default=""),
    teaching_methods_and_competencies: str = Form(default=""),
    subject_specific_skills: str = Form(default=""),
    additional_skills: str = Form(default=""),
    most_recent_school: str = Form(default=""),
    employment_status: str = Form(default=""),
    files: list[UploadFile] = File(default=[]),
):
    """Submit documents and run the first explainable screening pass."""
    vacancy = db.get(Vacancy, _parse_uuid(vacancy_id))
    if not vacancy or not vacancy.is_open:
        raise HTTPException(status_code=404, detail="Vacancy is not open")
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one CV or qualification document")
    if years_secondary_teaching_experience.strip():
        try:
            years = float(years_secondary_teaching_experience)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Teaching experience must be a non-negative number of years",
            ) from None
        if years < 0 or years > 60:
            raise HTTPException(
                status_code=422,
                detail="Teaching experience must be between 0 and 60 years",
            )
    if full_name.strip():
        if len(full_name.strip()) < 2:
            raise HTTPException(status_code=422, detail="Full name must contain at least 2 characters")
        user.full_name = full_name.strip()[:200]
    if phone.strip():
        user.phone = phone.strip()[:40]
    applicant_profile = user.profile
    if applicant_profile is None:
        applicant_profile = ApplicantProfile(user_id=user.id)
        db.add(applicant_profile)
        user.profile = applicant_profile
    if district.strip():
        applicant_profile.district = district.strip()[:120]

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
    details = {
        "highest_qualification": highest_qualification,
        "institution": institution,
        "graduation_year": graduation_year,
        "teaching_subject_specialization": teaching_subject_specialization,
        "years_secondary_teaching_experience": years_secondary_teaching_experience,
        "teaching_experience_summary": teaching_experience_summary,
        "professional_teaching_qualification_or_training": professional_teaching_qualification_or_training,
        "teaching_methods_and_competencies": teaching_methods_and_competencies,
        "subject_specific_skills": subject_specific_skills,
        "additional_skills": additional_skills,
        "most_recent_school": most_recent_school,
        "employment_status": employment_status,
    }
    _append_application_details(parsed, details)
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
            source_document_id=(
                application.documents[0].id
                if application.documents
                and not item.source_snippet.startswith("Application form:")
                else None
            ),
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


@router.post("/{application_id}/rescore", response_model=ApplicationResponse)
def rescore_application(
    application_id: str,
    db: DB,
    user: User = Depends(director_only),
):
    """Run and persist a fresh score using the current vacancy rubric."""
    application = _get_application(db, application_id)
    if not application.profile:
        raise HTTPException(
            status_code=409,
            detail="This application has no saved candidate profile to score",
        )

    outcome = score_application(application.profile, application.vacancy.criteria)
    result = ScreeningResult(
        application_id=application.id,
        total_score=outcome.total_score,
        scoring_version=outcome.scoring_version,
        run_at=datetime.utcnow(),
    )
    db.add(result)
    db.flush()
    criteria_by_id = {
        str(criterion.id): criterion
        for criterion in application.vacancy.criteria
    }
    for item in outcome.scores:
        criterion = criteria_by_id.get(item.criterion_id)
        if not criterion:
            continue
        evidence_item = _find_evidence_item(application.profile, item.evidence)
        db.add(CriterionScore(
            result_id=result.id,
            criterion_id=criterion.id,
            matched=item.matched,
            score=item.score,
            evidence_item_id=evidence_item.id if evidence_item else None,
            explanation=item.explanation,
        ))

    if application.status != "decided":
        application.status = (
            "needs_review"
            if application.profile.extraction_status == "needs_review"
            else "screened"
        )
    audit(db, "Screening run completed", user.id, "application", str(application.id), {
        "score": outcome.total_score,
        "rescore": True,
    })
    db.commit()
    db.refresh(application)
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
    vacancy_title = application.vacancy.title
    successful = payload.decision == "shortlist"
    reason = payload.note.strip() if payload.note else ("The Director selected you for the next stage." if successful else "No reason was provided.")
    message = (
        f"Congratulations! Your application for {vacancy_title} has been successful. Reason: {reason}"
        if successful else
        f"Your application for {vacancy_title} was unsuccessful. Reason: {reason} Thank you for your interest."
    )
    db.add(Notification(recipient_id=application.applicant_id, category="decision", title="Application decision", message=message))
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
