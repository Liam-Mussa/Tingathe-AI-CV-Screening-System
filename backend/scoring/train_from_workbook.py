"""Train the CV screening configuration from the provided Tingathe workbook.

This creates a deterministic rule-based model configuration. It does not imply
or store an ML version label.
"""
from collections import Counter
import json
from pathlib import Path

import openpyxl


def normalise(value):
    import re
    return re.sub(r"[^a-z0-9\s+]", " ", str(value).lower()).strip()


def train(workbook_path: Path, output_path: Path) -> dict:
    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)

    criteria_sheet = workbook["Scoring Criteria"]
    weights = {}
    for row in criteria_sheet.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        weights[normalise(row[0])] = float(row[1])

    applicants_sheet = workbook["Applicants"]
    headers = [normalise(value) for value in next(applicants_sheet.iter_rows(min_row=1, max_row=1, values_only=True))]

    subject_words = {}
    skill_counts = Counter()
    methodology_counts = Counter()
    for values in applicants_sheet.iter_rows(min_row=2, values_only=True):
        row = dict(zip(headers, values))
        subject = str(row.get("teaching subject specialization", "")).strip()
        if subject:
            key = normalise(subject)
            subject_words.setdefault(key, set()).update(normalise(subject).split())
            subject_words.setdefault(key, set()).update(normalise(str(row.get("subject specific skills", ""))).split())

        for field in ("teaching methods and competencies", "subject specific skills", "additional skills"):
            for skill in str(row.get(field, "")).replace(";", ",").split(","):
                skill = skill.strip()
                if skill:
                    skill_counts[normalise(skill)] += 1

        for skill in str(row.get("teaching methods and competencies", "")).replace(";", ",").split(","):
            skill = skill.strip()
            if skill:
                methodology_counts[normalise(skill)] += 1

    vacancies_sheet = workbook["Vacancies"]
    vacancy_headers = [normalise(value) for value in next(vacancies_sheet.iter_rows(min_row=1, max_row=1, values_only=True))]
    vacancy_subjects = {}
    for values in vacancies_sheet.iter_rows(min_row=2, values_only=True):
        row = dict(zip(vacancy_headers, values))
        vacancy_subjects[str(row.get("subjects", "")).strip()] = {
            "minimum_qualification": str(row.get("minimum qualification", "")),
            "minimum_experience": float(row.get("minimum experience years", 0) or 0),
            "required_skills": str(row.get("required skills", "")),
        }

    result = {
        "source": str(workbook_path.name),
        "criteria": weights,
        "subject_vocabularies": {key: sorted(words) for key, words in subject_words.items()},
        "top_skills": dict(skill_counts.most_common(50)),
        "methodology_skills": dict(methodology_counts.most_common(30)),
        "vacancies": vacancy_subjects,
    }
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    workbook = Path(r"G:\Academic\Projects\New folder\tingathe_secondary_teacher_demo\tingathe_demo_dataset.xlsx")
    output = Path(__file__).with_name("trained_model.json")
    result = train(workbook, output)
    print(json.dumps({"source": result["source"], "criteria": result["criteria"], "output": str(output)}, indent=2))
