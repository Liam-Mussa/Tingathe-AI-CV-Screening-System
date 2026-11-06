"""Public vacancy browsing and Director vacancy management."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api_helpers import DB, audit, director_only, optional_user, vacancy_response, _parse_uuid
from models import Category, User, Vacancy, VacancyCriterion
from schemas import VacancyRequest, VacancyResponse

router = APIRouter(prefix="/api/vacancies", tags=["vacancies"])


def _get_vacancy(db: Session, vacancy_id: str) -> Vacancy:
    vacancy = db.get(Vacancy, _parse_uuid(vacancy_id))
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy


def _category(db: Session, name: str) -> Category:
    category = db.query(Category).filter(Category.name == name.strip()).one_or_none()
    if category is None:
        category = Category(name=name.strip())
        db.add(category)
        db.flush()
    return category


def _replace_criteria(vacancy: Vacancy, criteria: list) -> None:
    vacancy.criteria.clear()
    vacancy.criteria.extend([
        VacancyCriterion(
            criterion_type=item.criterion_type,
            label=item.label.strip(),
            required_value=(item.required_value or item.label).strip(),
            weight=item.weight,
            is_mandatory=item.is_mandatory,
        )
        for item in criteria
        if item.label.strip()
    ])


@router.get("", response_model=list[VacancyResponse])
def list_vacancies(
    db: DB,
    user: User | None = Depends(optional_user),
):
    query = db.query(Vacancy).order_by(Vacancy.created_at.desc())
    if not user or user.role != "director":
        query = query.filter(
            Vacancy.status == "open",
            (Vacancy.closing_date.is_(None) | (Vacancy.closing_date >= date.today())),
        )
    return [vacancy_response(vacancy) for vacancy in query.all()]


@router.get("/{vacancy_id}", response_model=VacancyResponse)
def get_vacancy(
    vacancy_id: str,
    db: DB,
    user: User | None = Depends(optional_user),
):
    vacancy = _get_vacancy(db, vacancy_id)
    if vacancy.status != "open" and (not user or user.role != "director"):
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy_response(vacancy)


@router.post("", response_model=VacancyResponse, status_code=status.HTTP_201_CREATED)
def create_vacancy(
    payload: VacancyRequest,
    db: DB,
    user: User = Depends(director_only),
):
    if payload.status == "open" and not payload.criteria:
        raise HTTPException(status_code=400, detail="An open vacancy needs at least one criterion")
    category = _category(db, payload.category)
    vacancy = Vacancy(
        category_id=category.id,
        title=payload.title.strip(),
        summary=payload.summary,
        description=payload.description,
        employment_type=payload.employment_type,
        image_key=payload.image_key,
        status=payload.status,
        closing_date=payload.closing_date,
        created_by=user.id,
    )
    db.add(vacancy)
    db.flush()
    _replace_criteria(vacancy, payload.criteria)
    audit(db, "Created vacancy", user.id, "vacancy", str(vacancy.id), {"title": vacancy.title})
    db.commit()
    db.refresh(vacancy)
    return vacancy_response(vacancy)


@router.put("/{vacancy_id}", response_model=VacancyResponse)
def update_vacancy(
    vacancy_id: str,
    payload: VacancyRequest,
    db: DB,
    user: User = Depends(director_only),
):
    vacancy = _get_vacancy(db, vacancy_id)
    category = _category(db, payload.category)
    vacancy.category_id = category.id
    vacancy.title = payload.title.strip()
    vacancy.summary = payload.summary
    vacancy.description = payload.description
    vacancy.employment_type = payload.employment_type
    vacancy.image_key = payload.image_key
    vacancy.status = payload.status
    vacancy.closing_date = payload.closing_date
    _replace_criteria(vacancy, payload.criteria)
    audit(db, "Updated vacancy", user.id, "vacancy", str(vacancy.id), {"title": vacancy.title})
    db.commit()
    db.refresh(vacancy)
    return vacancy_response(vacancy)


@router.post("/{vacancy_id}/publish", response_model=VacancyResponse)
def publish_vacancy(
    vacancy_id: str,
    db: DB,
    user: User = Depends(director_only),
):
    vacancy = _get_vacancy(db, vacancy_id)
    if not vacancy.criteria:
        raise HTTPException(status_code=400, detail="Add at least one screening criterion before publishing")
    vacancy.status = "open"
    audit(db, "Published vacancy", user.id, "vacancy", str(vacancy.id), {"title": vacancy.title})
    db.commit()
    db.refresh(vacancy)
    return vacancy_response(vacancy)
