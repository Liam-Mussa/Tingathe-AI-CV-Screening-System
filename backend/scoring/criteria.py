"""Canonical screening criteria; these weights are application-wide constants."""

FIXED_SCORING_CRITERIA = (
    ("academic qualification", 25.0),
    ("teaching subject specialization", 25.0),
    ("teaching experience", 20.0),
    ("teaching methodology and classroom management", 15.0),
    ("professional teaching qualification/training", 10.0),
    ("additional relevant skills", 5.0),
)

FIXED_CRITERION_TYPES = {
    "academic qualification": "qualification",
    "teaching subject specialization": "skill",
    "teaching experience": "experience",
    "teaching methodology and classroom management": "keyword",
    "professional teaching qualification/training": "keyword",
    "additional relevant skills": "skill",
}


def criterion_key(value: str) -> str:
    """Normalize a criterion label for validation without changing its meaning."""
    import re

    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
