"""Build a deterministic screening configuration from the supplied data."""
import csv
from collections import Counter
import json
from pathlib import Path
import re
import sys

import openpyxl

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from scoring.criteria import FIXED_SCORING_CRITERIA, criterion_key


ROOT = BACKEND_DIR.parent
CRITERIA_BY_KEY = {
    criterion_key(label): (label, weight)
    for label, weight in FIXED_SCORING_CRITERIA
}


def normalise(value):
    return re.sub(r"[^a-z0-9\s+]", " ", str(value).lower()).strip()


def _read_fixed_criteria(path: Path) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    actual = {
        criterion_key(row["criterion"]): float(row["weight_percent"])
        for row in rows
    }
    if actual != {key: weight for key, (_, weight) in CRITERIA_BY_KEY.items()}:
        raise ValueError(
            f"{path.name} must contain the six canonical criteria and their fixed weights"
        )
    return {
        label: weight
        for label, weight in FIXED_SCORING_CRITERIA
    }


def _read_vacancies(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    required = {
        "vacancy_id", "job_title", "subjects", "minimum_qualification",
        "minimum_experience_years", "required_skills", "location",
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"{path.name} is missing one or more required vacancy columns")
    return {
        row["subjects"].strip(): {
            "vacancy_id": row["vacancy_id"].strip(),
            "job_title": row["job_title"].strip(),
            "minimum_qualification": row["minimum_qualification"].strip(),
            "minimum_experience": float(row["minimum_experience_years"]),
            "required_skills": row["required_skills"].strip(),
            "location": row["location"].strip(),
        }
        for row in rows
    }


def train(
    workbook_path: Path | None = None,
    output_path: Path | None = None,
    criteria_path: Path | None = None,
    vacancies_path: Path | None = None,
) -> dict:
    workbook_path = workbook_path or ROOT / "tingathe_demo_dataset.xlsx"
    output_path = output_path or Path(__file__).with_name("trained_model.json")
    criteria_path = criteria_path or ROOT / "scoring_criteria.csv"
    vacancies_path = vacancies_path or ROOT / "vacancies.csv"

    criteria = _read_fixed_criteria(criteria_path)
    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    if not {"Applicants", "Scoring Criteria"}.issubset(workbook.sheetnames):
        raise ValueError("Workbook must contain Applicants and Scoring Criteria sheets")

    workbook_criteria = {}
    for name, weight, *_ in workbook["Scoring Criteria"].iter_rows(
        min_row=2, values_only=True
    ):
        if name:
            workbook_criteria[criterion_key(str(name))] = float(weight)
    expected = {criterion_key(label): weight for label, weight in FIXED_SCORING_CRITERIA}
    if workbook_criteria != expected:
        raise ValueError("Workbook scoring criteria differ from the fixed scoring criteria")

    applicants_sheet = workbook["Applicants"]
    headers = [
        normalise(value)
        for value in next(
            applicants_sheet.iter_rows(min_row=1, max_row=1, values_only=True)
        )
    ]
    subject_words = {}
    skill_counts = Counter()
    methodology_counts = Counter()
    applicant_count = 0
    for values in applicants_sheet.iter_rows(min_row=2, values_only=True):
        row = dict(zip(headers, values))
        if not any(value is not None for value in values):
            continue
        applicant_count += 1
        subject = str(row.get("teaching subject specialization") or "").strip()
        if subject:
            key = normalise(subject)
            subject_words.setdefault(key, set()).update(key.split())
            subject_words[key].update(
                normalise(str(row.get("subject specific skills") or "")).split()
            )

        for field in (
            "teaching methods and competencies",
            "subject specific skills",
            "additional skills",
        ):
            for skill in str(row.get(field) or "").replace(";", ",").split(","):
                if skill.strip():
                    skill_counts[normalise(skill.strip())] += 1

        for skill in str(row.get("teaching methods and competencies") or "").replace(
            ";", ","
        ).split(","):
            if skill.strip():
                methodology_counts[normalise(skill.strip())] += 1

    result = {
        "source": workbook_path.name,
        "vacancy_source": vacancies_path.name,
        "applicant_records_used": applicant_count,
        "criteria": criteria,
        "subject_vocabularies": {
            key: sorted(words) for key, words in subject_words.items()
        },
        "top_skills": dict(skill_counts.most_common(50)),
        "methodology_skills": dict(methodology_counts.most_common(30)),
        "vacancies": _read_vacancies(vacancies_path),
    }
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    workbook.close()
    return result


if __name__ == "__main__":
    trained = train()
    print(json.dumps({
        "applicant_records_used": trained["applicant_records_used"],
        "vacancy_count": len(trained["vacancies"]),
        "criteria": trained["criteria"],
        "output": str(Path(__file__).with_name("trained_model.json")),
    }, indent=2))
