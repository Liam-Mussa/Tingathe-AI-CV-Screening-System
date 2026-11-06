"""SQLAlchemy models, mirroring backend/schema.sql.

UUIDs are stored as strings so the same models work on PostgreSQL (where a
native uuid type exists) and on SQLite (where it does not). The table names,
constraints and relationships match the PostgreSQL schema so switching the
DATABASE_URL is the only change needed.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String,
    Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from database import Base


class GUID(TypeDecorator):
    """A cross-database UUID column: native uuid on PostgreSQL, CHAR(36) on SQLite."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=_uuid)
    email = Column(String(320), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(40))
    role = Column(String(20), nullable=False, default="applicant")  # applicant | director
    is_active = Column(Boolean, nullable=False, default=True)
    preferred_language = Column(String(10), nullable=False, default="en")
    created_at = Column(DateTime, nullable=False, default=_now)

    profile = relationship("ApplicantProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="applicant", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="decider")

    @property
    def is_director(self) -> bool:
        return self.role == "director"


class ApplicantProfile(Base):
    __tablename__ = "applicant_profiles"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    district = Column(String(120))
    consent_at = Column(DateTime)

    user = relationship("User", back_populates="profile")


class Category(Base):
    __tablename__ = "categories"

    id = Column(GUID(), primary_key=True, default=_uuid)
    name = Column(String(120), unique=True, nullable=False)
    description = Column(Text)

    vacancies = relationship("Vacancy", back_populates="category")


class Vacancy(Base):
    __tablename__ = "vacancies"

    id = Column(GUID(), primary_key=True, default=_uuid)
    category_id = Column(GUID(), ForeignKey("categories.id"))
    title = Column(String(200), nullable=False)
    summary = Column(Text)
    description = Column(Text)
    employment_type = Column(String(40))
    image_key = Column(String(60))
    status = Column(String(20), nullable=False, default="draft")  # draft | open | closed | archived
    closing_date = Column(Date)
    created_by = Column(GUID(), ForeignKey("users.id"))
    created_at = Column(DateTime, nullable=False, default=_now)

    category = relationship("Category", back_populates="vacancies")
    criteria = relationship("VacancyCriterion", back_populates="vacancy", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="vacancy", cascade="all, delete-orphan")

    @property
    def is_open(self) -> bool:
        return self.status == "open" and (self.closing_date is None or self.closing_date >= date.today())


class VacancyCriterion(Base):
    __tablename__ = "vacancy_criteria"

    id = Column(GUID(), primary_key=True, default=_uuid)
    vacancy_id = Column(GUID(), ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False)
    criterion_type = Column(String(20), nullable=False)  # qualification | skill | experience | keyword
    label = Column(String(200), nullable=False)
    required_value = Column(String(200))
    weight = Column(Numeric(6, 2), nullable=False, default=0)
    is_mandatory = Column(Boolean, nullable=False, default=False)

    vacancy = relationship("Vacancy", back_populates="criteria")
    scores = relationship("CriterionScore", back_populates="criterion")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("vacancy_id", "applicant_id", name="uq_application_per_vacancy"),)

    id = Column(GUID(), primary_key=True, default=_uuid)
    vacancy_id = Column(GUID(), ForeignKey("vacancies.id"), nullable=False)
    applicant_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="submitted")  # submitted | processing | screened | needs_review | decided
    cover_note = Column(Text)
    submitted_at = Column(DateTime, nullable=False, default=_now)

    vacancy = relationship("Vacancy", back_populates="applications")
    applicant = relationship("User", back_populates="applications")
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    profile = relationship("CandidateProfile", back_populates="application", uselist=False, cascade="all, delete-orphan")
    results = relationship("ScreeningResult", back_populates="application", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="application", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, default=_uuid)
    application_id = Column(GUID(), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(String(20), nullable=False, default="other")  # cv | qualification | other
    original_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    mime_type = Column(String(120))
    size_bytes = Column(Integer)
    sha256 = Column(String(64))
    uploaded_at = Column(DateTime, nullable=False, default=_now)

    application = relationship("Application", back_populates="documents")
    runs = relationship("ExtractionRun", back_populates="document", cascade="all, delete-orphan")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id = Column(GUID(), primary_key=True, default=_uuid)
    document_id = Column(GUID(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    method = Column(String(20), nullable=False)  # pdf_text | docx | ocr
    status = Column(String(20), nullable=False)  # ok | partial | failed
    text_content = Column(Text)
    confidence = Column(Numeric(4, 3))
    warnings = Column(JSON)
    finished_at = Column(DateTime)

    document = relationship("Document", back_populates="runs")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(GUID(), primary_key=True, default=_uuid)
    application_id = Column(GUID(), ForeignKey("applications.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_experience_months = Column(Integer)
    extraction_status = Column(String(20), nullable=False, default="ok")  # ok | needs_review
    built_at = Column(DateTime, nullable=False, default=_now)

    application = relationship("Application", back_populates="profile")
    items = relationship("ProfileItem", back_populates="profile", cascade="all, delete-orphan")


class ProfileItem(Base):
    __tablename__ = "profile_items"

    id = Column(GUID(), primary_key=True, default=_uuid)
    profile_id = Column(GUID(), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(20), nullable=False)  # education | skill | qualification | experience
    value = Column(String(300), nullable=False)
    institution = Column(String(200))
    start_date = Column(Date)
    end_date = Column(Date)
    source_document_id = Column(GUID(), ForeignKey("documents.id"))
    source_snippet = Column(Text)
    confidence = Column(Numeric(4, 3))

    profile = relationship("CandidateProfile", back_populates="items")


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(GUID(), primary_key=True, default=_uuid)
    application_id = Column(GUID(), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    total_score = Column(Numeric(5, 2), nullable=False, default=0)
    rank = Column(Integer)
    scoring_version = Column(String(40), nullable=False, default="v1")
    run_at = Column(DateTime, nullable=False, default=_now)

    application = relationship("Application", back_populates="results")
    scores = relationship("CriterionScore", back_populates="result", cascade="all, delete-orphan")


class CriterionScore(Base):
    __tablename__ = "criterion_scores"

    id = Column(GUID(), primary_key=True, default=_uuid)
    result_id = Column(GUID(), ForeignKey("screening_results.id", ondelete="CASCADE"), nullable=False)
    criterion_id = Column(GUID(), ForeignKey("vacancy_criteria.id"), nullable=False)
    matched = Column(Boolean, nullable=False, default=False)
    score = Column(Numeric(6, 2), nullable=False, default=0)
    evidence_item_id = Column(GUID(), ForeignKey("profile_items.id"))
    explanation = Column(Text)

    result = relationship("ScreeningResult", back_populates="scores")
    criterion = relationship("VacancyCriterion", back_populates="scores")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(GUID(), primary_key=True, default=_uuid)
    application_id = Column(GUID(), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    decided_by = Column(GUID(), ForeignKey("users.id"), nullable=False)
    decision = Column(String(20), nullable=False)  # shortlist | hold | not_shortlisted
    note = Column(Text)
    decided_at = Column(DateTime, nullable=False, default=_now)

    application = relationship("Application", back_populates="decisions")
    decider = relationship("User", back_populates="decisions")


class ReportExport(Base):
    __tablename__ = "report_exports"

    id = Column(GUID(), primary_key=True, default=_uuid)
    vacancy_id = Column(GUID(), ForeignKey("vacancies.id"), nullable=False)
    generated_by = Column(GUID(), ForeignKey("users.id"), nullable=False)
    format = Column(String(10), nullable=False)  # pdf | csv
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(GUID(), ForeignKey("users.id"))
    action = Column(String(200), nullable=False)
    entity_type = Column(String(60))
    entity_id = Column(String(64))
    # Named "extra" because "metadata" is reserved by the declarative base.
    extra = Column("metadata", JSON)
    created_at = Column(DateTime, nullable=False, default=_now)
