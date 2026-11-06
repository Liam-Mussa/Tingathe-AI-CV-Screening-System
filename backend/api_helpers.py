"""Shared API dependencies and serializers."""
from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from config import MAX_UPLOAD_MB
from database import get_db
from models import (
    Application,
    AuditLog,
    Category,
    CriterionScore,
    Decision,
    Document,
    ExtractionRun,
    ScreeningResult,
    User,
    Vacancy,
)
from schemas import (
    ApplicationResponse,
    AuditResponse,
    CriterionResponse,
    CriterionScoreResponse,
    UserResponse,
    VacancyResponse,
)
from security import decode_token

DB = Annotated[Session, Depends(get_db)]

STATUS_LABELS = {
    "submitted": (0, "Received"),
    "processing": (1, "Processing"),
    "screened": (2, "Under review"),
    "needs_review": (2, "Under review"),
    "decided": (3, "Decision"),
}
DECISION_LABELS = {
    "shortlist": "Shortlisted",
    "hold": "Hold",
    "not_shortlisted": "Not shortlisted",
}


def _parse_uuid(value: str):
    """Let SQLAlchemy's GUID type validate identifiers consistently."""
    import uuid

    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Resource not found") from None


def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    claims = decode_token(authorization.split(" ", 1)[1].strip())
    if not claims or not claims.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.get(User, _parse_uuid(claims["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing")
    return user


def director_only(user: User = Depends(current_user)) -> User:
    if user.role != "director":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director access required")
    return user


def optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    claims = decode_token(authorization.split(" ", 1)[1].strip())
    if not claims or not claims.get("sub"):
        return None
    user = db.get(User, _parse_uuid(claims["sub"]))
    return user if user and user.is_active else None


def _date_text(value: date | None) -> str | None:
    return value.strftime("%d %b %Y") if value else None


def _criterion_response(criterion) -> CriterionResponse:
    return CriterionResponse(
        id=str(criterion.id),
        criterion_type=criterion.criterion_type,
        label=criterion.label,
        required_value=criterion.required_value,
        weight=float(criterion.weight or 0),
        is_mandatory=criterion.is_mandatory,
    )


def vacancy_response(vacancy: Vacancy) -> VacancyResponse:
    category = vacancy.category.name if vacancy.category else "General"
    criteria = [_criterion_response(c) for c in vacancy.criteria]
    return VacancyResponse(
        id=str(vacancy.id),
        title=vacancy.title,
        category=category,
        cat=category,
        summary=vacancy.summary,
        description=vacancy.description,
        employment_type=vacancy.employment_type,
        type=vacancy.employment_type,
        image_key=vacancy.image_key,
        img=vacancy.image_key,
        status=vacancy.status,
        closing_date=vacancy.closing_date,
        closes=_date_text(vacancy.closing_date),
        applicants=len(vacancy.applications),
        criteria=criteria,
        created_at=vacancy.created_at,
    )


def _latest_result(application: Application) -> ScreeningResult | None:
    return max(application.results, key=lambda result: result.run_at or datetime.min, default=None)


def _latest_extraction(document: Document) -> ExtractionRun | None:
    return max(document.runs, key=lambda run: run.finished_at or datetime.min, default=None)


def application_response(application: Application) -> ApplicationResponse:
    status_value, status_label = STATUS_LABELS.get(application.status, (0, "Received"))
    result = _latest_result(application)
    decision = max(application.decisions, key=lambda item: item.decided_at or datetime.min, default=None)
    criterion_scores = []
    score_values = None
    warnings: list[str] = []
    if result:
        score_values = [float(item.score or 0) for item in result.scores]
        criterion_scores = [
            CriterionScoreResponse(
                criterion_id=str(item.criterion_id),
                label=item.criterion.label,
                criterion_type=item.criterion.criterion_type,
                matched=item.matched,
                score=float(item.score or 0),
                weight=float(item.criterion.weight or 0),
                explanation=item.explanation or "No explanation recorded.",
                evidence=item.evidence_item_id and next(
                    (profile_item.source_snippet or profile_item.value
                     for profile_item in (application.profile.items if application.profile else [])
                     if profile_item.id == item.evidence_item_id),
                    None,
                ),
            )
            for item in result.scores
        ]
    for document in application.documents:
        run = _latest_extraction(document)
        if run and run.warnings:
            warnings.extend(str(warning) for warning in run.warnings)

    names = [document.original_name for document in application.documents]
    score = float(result.total_score) if result else None
    decision_value = decision.decision if decision else "undecided"
    decision_text = DECISION_LABELS.get(decision_value, "Undecided")
    submitted = application.submitted_at
    return ApplicationResponse(
        id=str(application.id),
        vacancy_id=str(application.vacancy_id),
        vacancyId=str(application.vacancy_id),
        vacancy_title=application.vacancy.title if application.vacancy else None,
        applicant_id=str(application.applicant_id),
        name=application.applicant.full_name,
        phone=application.applicant.phone,
        note=application.cover_note,
        cover_note=application.cover_note,
        files=names,
        extraction_status="Review" if warnings or (application.profile and application.profile.extraction_status == "needs_review") else "Complete",
        ext="Review" if warnings or (application.profile and application.profile.extraction_status == "needs_review") else "Complete",
        score=score,
        status=status_value,
        status_label=status_label,
        decision=decision_text,
        decided_by=decision.decider.full_name if decision and decision.decider else None,
        decidedBy=decision.decider.full_name if decision and decision.decider else None,
        created_at=submitted,
        createdAt=submitted.date().isoformat() if submitted else None,
        scores=score_values,
        criterion_scores=criterion_scores,
        warnings=warnings,
    )


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        name=user.full_name,
        phone=user.phone,
        district=user.profile.district if user.profile else None,
        role=user.role,
        preferred_language=user.preferred_language,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def audit_response(entry: AuditLog, db: Session) -> AuditResponse:
    actor = db.get(User, entry.actor_id) if entry.actor_id else None
    item = entry.entity_id or entry.entity_type
    return AuditResponse(
        id=entry.id,
        actor=actor.full_name if actor else "System",
        action=entry.action,
        item=item,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        metadata=entry.extra,
        created_at=entry.created_at,
        row=[actor.full_name if actor else "System", entry.action, item or ""],
    )


def audit(
    db: Session,
    action: str,
    actor_id=None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        extra=metadata,
    )
    db.add(entry)
    return entry


def validate_upload_size(size: int) -> None:
    if size > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_UPLOAD_MB} MB upload limit")
