"""Idempotent development data for a first local API run."""
from datetime import date

from sqlalchemy.orm import Session

from models import Category, User, Vacancy, VacancyCriterion
from security import hash_password

SEED_VACANCIES = [
    {
        "title": "Mathematics Teacher",
        "category": "Teaching",
        "employment_type": "Full time",
        "status": "open",
        "closing_date": date(2026, 11, 14),
        "image_key": "maths",
        "summary": "Teach Mathematics to Forms 1–4 and support the department.",
        "criteria": [
            ("qualification", "Degree in Mathematics Education", "BSc Mathematics Education", 30, True),
            ("qualification", "Teaching registration", "teaching registration", 15, False),
            ("experience", "Classroom experience (3+ years)", "3 years", 25, True),
            ("skill", "Curriculum planning, assessment", "curriculum planning assessment", 20, False),
            ("skill", "ICT in teaching", "ICT in teaching", 10, False),
        ],
    },
    {
        "title": "Physical Science Teacher",
        "category": "Teaching",
        "employment_type": "Full time",
        "status": "open",
        "closing_date": date(2026, 11, 21),
        "image_key": "science",
        "summary": "Lead practical science lessons and laboratory safety.",
        "criteria": [
            ("qualification", "Degree in Science Education", "science education", 30, True),
            ("qualification", "Teaching registration", "teaching registration", 15, False),
            ("experience", "Laboratory and practical experience", "2 years", 25, False),
            ("keyword", "Safety procedures and risk assessment", "safety risk assessment", 20, True),
            ("skill", "ICT in teaching", "ICT in teaching", 10, False),
        ],
    },
    {
        "title": "School Accountant",
        "category": "Non-teaching",
        "employment_type": "Full time",
        "status": "open",
        "closing_date": date(2026, 11, 28),
        "image_key": "accounts",
        "summary": "Manage school accounts, fees records and reporting.",
        "criteria": [
            ("qualification", "Diploma or degree in Accounting", "accounting", 35, True),
            ("qualification", "ACCA or professional qualification", "ACCA", 15, False),
            ("experience", "School fees and ledger experience", "school fees ledger", 25, False),
            ("skill", "Excel and accounting software", "Excel accounting software", 15, False),
            ("keyword", "Payroll and statutory reporting", "payroll statutory reporting", 10, False),
        ],
    },
    {
        "title": "School Librarian",
        "category": "Non-teaching",
        "employment_type": "Part time",
        "status": "draft",
        "closing_date": None,
        "image_key": "library",
        "summary": "Run the library and promote reading across the school.",
        "criteria": [
            ("qualification", "Diploma in Library Science", "library science", 35, True),
            ("experience", "Experience running a school library", "school library", 25, False),
            ("keyword", "Reading promotion programmes", "reading promotion", 20, False),
            ("skill", "Cataloguing and ICT systems", "cataloguing ICT", 20, False),
        ],
    },
    {
        "title": "English Teacher",
        "category": "Teaching",
        "employment_type": "Full time",
        "status": "closed",
        "closing_date": date(2026, 9, 30),
        "image_key": "english",
        "summary": "Teach English language and literature to Forms 1–4.",
        "criteria": [
            ("qualification", "Degree in English Education", "English Education", 30, True),
            ("qualification", "Teaching registration", "teaching registration", 15, False),
            ("skill", "Literature and language teaching", "literature language teaching", 25, True),
            ("skill", "Curriculum planning and assessment", "curriculum planning assessment", 20, False),
            ("skill", "ICT in teaching", "ICT in teaching", 10, False),
        ],
    },
]


def seed_development_data(db: Session) -> None:
    """Create the local Director, categories, vacancies and criteria once."""
    director = db.query(User).filter(User.email == "william@example.com").one_or_none()
    if director is None:
        director = User(
            email="william@example.com",
            password_hash=hash_password("director123"),
            full_name="William Mussa",
            role="director",
            phone="+265 999 000 000",
        )
        db.add(director)
        db.flush()

    applicant = db.query(User).filter(User.email == "chikondi@example.com").one_or_none()
    if applicant is None:
        applicant = User(
            email="chikondi@example.com",
            password_hash=hash_password("applicant123"),
            full_name="Chikondi Banda",
            role="applicant",
            phone="+265 991 234 567",
        )
        db.add(applicant)
        db.flush()

    existing_titles = {title for (title,) in db.query(Vacancy.title).all()}
    for item in SEED_VACANCIES:
        if item["title"] in existing_titles:
            continue
        category = db.query(Category).filter(Category.name == item["category"]).one_or_none()
        if category is None:
            category = Category(name=item["category"])
            db.add(category)
            db.flush()
        vacancy = Vacancy(
            category_id=category.id,
            title=item["title"],
            summary=item["summary"],
            description=item["summary"],
            employment_type=item["employment_type"],
            image_key=item["image_key"],
            status=item["status"],
            closing_date=item["closing_date"],
            created_by=director.id,
        )
        db.add(vacancy)
        db.flush()
        db.add_all([
            VacancyCriterion(
                vacancy_id=vacancy.id,
                criterion_type=criterion_type,
                label=label,
                required_value=required,
                weight=weight,
                is_mandatory=mandatory,
            )
            for criterion_type, label, required, weight, mandatory in item["criteria"]
        ])

    db.commit()
