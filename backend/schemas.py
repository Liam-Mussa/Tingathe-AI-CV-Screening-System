"""Pydantic request and response contracts for the API.

The database uses UUIDs and snake_case names. The response models intentionally
also expose a few frontend-friendly aliases (for example ``cat`` and
``closing_date``) so the React client can consume the API without knowing the
storage details.
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    district: str | None = Field(default=None, max_length=120)
    preferred_language: str = Field(default="en", max_length=10)
    consent: bool = False


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class UserResponse(APIModel):
    id: str
    email: str
    full_name: str
    name: str | None = None
    phone: str | None = None
    district: str | None = None
    role: Literal["applicant", "director"]
    preferred_language: str = "en"
    is_active: bool = True
    created_at: datetime | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class CriterionRequest(BaseModel):
    criterion_type: Literal["qualification", "skill", "experience", "keyword"] = "keyword"
    label: str = Field(min_length=1, max_length=200)
    required_value: str | None = Field(default=None, max_length=200)
    weight: float = Field(default=0, ge=0, le=100)
    is_mandatory: bool = False


class CriterionResponse(APIModel):
    id: str
    criterion_type: str
    label: str
    required_value: str | None = None
    weight: float
    is_mandatory: bool = False


class VacancyRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(default="General", min_length=1, max_length=120)
    summary: str | None = None
    description: str | None = None
    employment_type: str | None = Field(default=None, max_length=40)
    image_key: str | None = Field(default=None, max_length=60)
    status: Literal["draft", "open", "closed", "archived"] = "draft"
    closing_date: date | None = None
    criteria: list[CriterionRequest] = Field(default_factory=list)


class VacancyResponse(APIModel):
    id: str
    title: str
    category: str = "General"
    cat: str = "General"
    summary: str | None = None
    description: str | None = None
    employment_type: str | None = None
    type: str | None = None
    image_key: str | None = None
    img: str | None = None
    status: str
    closing_date: date | None = None
    closes: str | None = None
    applicants: int = 0
    criteria: list[CriterionResponse] = Field(default_factory=list)
    created_at: datetime | None = None


class ApplicationDecisionRequest(BaseModel):
    decision: Literal["shortlist", "hold", "not_shortlisted"]
    note: str | None = Field(default=None, max_length=5000)


class CriterionScoreResponse(APIModel):
    criterion_id: str
    label: str
    criterion_type: str
    matched: bool
    score: float
    weight: float
    explanation: str
    evidence: str | None = None


class ApplicationResponse(APIModel):
    id: str
    vacancy_id: str
    vacancyId: str | None = None
    vacancy_title: str | None = None
    legacy_vacancy_id: int | None = None
    applicant_id: str
    name: str
    phone: str | None = None
    note: str | None = None
    cover_note: str | None = None
    files: list[str] = Field(default_factory=list)
    extraction_status: str | None = None
    ext: str | None = None
    score: float | None = None
    status: int = 0
    status_label: str = "Received"
    decision: str = "Undecided"
    decided_by: str | None = None
    decidedBy: str | None = None
    created_at: datetime | None = None
    createdAt: str | None = None
    scores: list[float] | None = None
    criterion_scores: list[CriterionScoreResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AuditResponse(BaseModel):
    id: int
    actor: str = "System"
    action: str
    item: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    metadata: dict | None = None
    created_at: datetime | None = None
    row: list[str] = Field(default_factory=list)


class ReportResponse(BaseModel):
    format: Literal["csv", "pdf"]
    filename: str
    download_url: str
