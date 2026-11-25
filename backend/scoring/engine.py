"""Score a candidate against a vacancy's criteria.

How scoring works
-----------------
Every criterion carries a weight. The scorer looks for evidence in the
candidate's profile and awards the criterion's full weight when it is clearly
met, a partial score when it is partly met, and zero when it is not met at all.
The result is a total out of 100 plus a per-criterion breakdown, each with a
sentence a director can read.

Mandatory criteria are handled separately: failing one caps the total so a
candidate who lacks a non-negotiable requirement cannot be ranked top.
"""
import json
import re
from pathlib import Path
from dataclasses import dataclass, field

# Words that add nothing when matching a skill or qualification.
STOP_WORDS = {
    "and", "or", "the", "a", "an", "of", "in", "with", "for", "to", "at",
    "on", "by", "from", "experience", "skills", "knowledge", "ability",
    "proficiency", "understanding", "strong", "good", "excellent", "demonstrated",
}

DATASET_CRITERIA = {
    "academic qualification": 25,
    "teaching subject specialization": 25,
    "teaching experience": 20,
    "teaching methodology and classroom management": 15,
    "professional teaching qualification/training": 10,
    "additional relevant skills": 5,
}

SUBJECT_ALIASES = {
    "mathematics": {"mathematics", "math", "algebra", "geometry", "statistics", "trigonometry", "mechanics"},
    "biology": {"biology", "ecology", "human biology", "plant biology", "laboratory", "practical"},
    "english": {"english", "grammar", "composition", "literature", "reading comprehension"},
    "computer studies": {"computer", "ict", "computer studies", "programming", "office applications", "laboratory"},
}

QUALIFICATION_LEVELS = (
    ("doctorate", 7), ("phd", 7), ("master", 6), ("mba", 6), ("bachelor", 5),
    ("advanced diploma", 4), ("higher diploma", 4), ("diploma", 3),
    ("certificate", 2), ("msce", 1), ("o level", 1), ("a level", 1),
)


@dataclass
class CriterionScoreData:
    """The score for one criterion, with its explanation."""

    criterion_id: str
    criterion_type: str
    label: str
    weight: float
    matched: bool
    score: float
    explanation: str
    evidence: str = ""


@dataclass
class ScoringOutcome:
    """The full result of scoring one application."""

    total_score: float
    scores: list = field(default_factory=list)
    mandatory_failures: list = field(default_factory=list)
    scoring_version: str = "dataset-trained"


def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace, drop punctuation."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s+#]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> set:
    return {t for t in _normalise(text).split() if t not in STOP_WORDS and len(t) > 1}


def _haystack(profile) -> str:
    """All of a candidate's profile text, used for matching."""
    parts = []
    for item in profile.items:
        parts.append(item.value)
        if getattr(item, "institution", None):
            parts.append(item.institution)
        parts.append(item.source_snippet or "")
    return _normalise(" ".join(parts))


def _match_ratio(need: str, have_tokens: set, have_text: str) -> float:
    """How much of a requirement is present, from 0 to 1.

    A requirement like "BSc Mathematics Education" matches when its distinctive
    tokens are present. Requiring every token would be brittle; requiring only
    one would be too loose, so most of the meaningful tokens must appear.
    """
    need_tokens = _tokens(need)
    if not need_tokens:
        return 0.0
    hits = sum(1 for t in need_tokens if t in have_tokens)
    ratio = hits / len(need_tokens)
    # A long phrase fully present scores even higher.
    if _normalise(need) and _normalise(need) in have_text:
        ratio = max(ratio, 0.95)
    return ratio


def score_application(profile, criteria) -> ScoringOutcome:
    """Score a parsed candidate profile against a vacancy's criteria.

    `criteria` is a list of objects with `id`, `criterion_type`, `label`,
    `required_value`, `weight` and `is_mandatory`.
    """
    have_tokens = _tokens(_haystack(profile))
    have_text = _haystack(profile)

    total_weight = sum(float(c.weight or 0) for c in criteria) or 1.0
    raw_total = 0.0
    scores: list = []
    mandatory_failures: list = []

    for criterion in criteria:
        weight = float(criterion.weight or 0)
        label = criterion.label
        ctype = criterion.criterion_type
        required = getattr(criterion, "required_value", None) or label
        dataset_weight = _dataset_weight(label)
        if dataset_weight is not None:
            weight = dataset_weight

        category = _dataset_category(label)
        if category == "teaching subject specialization":
            matched, awarded, evidence, explanation = _score_subject_specialization(profile, required, have_text, weight)
        elif category == "professional teaching qualification/training":
            matched, awarded, evidence, explanation = _score_professional_training(profile, have_text, weight)
        elif category == "teaching methodology and classroom management":
            matched, awarded, evidence, explanation = _score_methodology(have_text, weight)
        elif category == "additional relevant skills":
            matched, awarded, evidence, explanation = _score_additional_skills(have_text, weight)
        elif ctype == "experience":
            matched, awarded, evidence, explanation = _score_experience(profile, required, weight)
        elif ctype == "qualification":
            matched, awarded, evidence, explanation = _score_qualification(
                profile, required, have_tokens, have_text, weight
            )
        elif ctype == "skill":
            matched, awarded, evidence, explanation = _score_skill(
                profile, required, have_tokens, have_text, weight
            )
        else:  # keyword and anything unknown
            matched, awarded, evidence, explanation = _score_keyword(
                profile, required, have_tokens, have_text, weight
            )

        if getattr(criterion, "is_mandatory", False) and not matched:
            mandatory_failures.append(label)

        raw_total += awarded
        scores.append(CriterionScoreData(
            criterion_id=str(criterion.id),
            criterion_type=ctype,
            label=label,
            weight=weight,
            matched=matched,
            score=round(awarded, 2),
            explanation=explanation,
            evidence=evidence,
        ))

    # Scale to a 0-100 total.
    total = round((raw_total / total_weight) * 100.0, 2)

    # Failing a mandatory requirement caps the score: an unqualified candidate
    # must not outrank a qualified one on the strength of soft criteria alone.
    if mandatory_failures:
        cap = 49.0
        total = min(total, cap)

    return ScoringOutcome(total_score=total, scores=scores, mandatory_failures=mandatory_failures)


def _evidence_from(profile, snippet: str) -> str:
    """Find the profile item whose text best matches a snippet, for citation."""
    best = ""
    best_ratio = 0.0
    want = _tokens(snippet)
    for item in profile.items:
        candidate = _tokens(f"{item.value} {getattr(item, 'institution', None) or ''}")
        if not want:
            continue
        ratio = sum(1 for t in want if t in candidate) / len(want)
        if ratio > best_ratio:
            best_ratio = ratio
            best = item.source_snippet or item.value
    return best


def _score_qualification(profile, required, have_tokens, have_text, weight):
    quals = profile.by_type("qualification")
    required_level = _qualification_level(required)
    best_item = None
    best_result = (0.0, 0.0)

    for item in quals:
        candidate_text = f"{item.value} {getattr(item, 'institution', None) or ''}"
        candidate_level = _qualification_level(candidate_text)
        field_ratio = _match_ratio(required, _tokens(candidate_text), _normalise(candidate_text))

        if required_level:
            if candidate_level == required_level:
                ratio = 1.0 if field_ratio >= 0.60 else 0.35
            elif candidate_level > required_level:
                subject_required = _tokens(re.sub(r"\b(bachelor|master|doctorate|phd|diploma|advanced diploma|higher diploma|certificate|mba)\b", " ", required))
                subject_candidate = _tokens(re.sub(r"\b(bachelor|master|doctorate|phd|diploma|advanced diploma|higher diploma|certificate|mba)\b", " ", candidate_text))
                shared_subject = bool(subject_required & subject_candidate)
                ratio = 1.0 if (field_ratio >= 0.60 or shared_subject) else 0.50
            elif candidate_level == 3 and required_level == 5:
                ratio = 0.50
            elif candidate_level == 4 and required_level == 5:
                ratio = 0.50
            else:
                ratio = 0.0
        else:
            ratio = field_ratio

        if ratio > best_result[0]:
            best_result = (ratio, candidate_level)
            best_item = item

    evidence = (best_item.source_snippet or best_item.value) if best_item else ""
    ratio = best_result[0]
    if ratio >= 0.95:
        return True, weight, evidence, f"Qualification meets '{required}'."
    if ratio >= 0.60:
        return True, weight * ratio, evidence, f"The qualification is above or closely related to '{required}'."
    if ratio > 0:
        return False, weight * ratio, evidence, f"The qualification is lower or only partially relevant to '{required}'."
    return False, 0.0, evidence, f"The qualification does not meet '{required}' at the required level."


def _score_skill(profile, required, have_tokens, have_text, weight):
    ratio = _match_ratio(required, have_tokens, have_text)
    evidence = _evidence_from(profile, required)
    if ratio >= 0.6:
        return True, weight, evidence, f"Skill '{required}' is stated in the CV."
    if ratio > 0:
        return False, weight * 0.5, evidence, (
            f"Partial match: a related skill to '{required}' appears, but not that exact skill."
        )
    return False, 0.0, "", f"Skill '{required}' was not found in the CV."


def _score_keyword(profile, required, have_tokens, have_text, weight):
    ratio = _match_ratio(required, have_tokens, have_text)
    evidence = _evidence_from(profile, required)
    if ratio >= 0.6:
        return True, weight, evidence, f"'{required}' appears in the CV."
    if ratio > 0:
        return False, weight * 0.5, evidence, f"'{required}' is partially matched in the CV."
    return False, 0.0, "", f"'{required}' does not appear in the CV."


def _score_professional_training(profile, have_text, weight):
    low = _normalise(have_text)
    evidence_terms = ("teacher education", "teaching practice", "professional teaching", "b ed", "education")
    evidence = next((term for term in evidence_terms if term in low), "")
    if evidence:
        return True, weight, evidence, "Explicit professional teaching education or training is stated."
    return False, 0.0, "", "No explicit professional teaching qualification or training was stated."


def _score_methodology(have_text, weight):
    terms = ("lesson planning", "classroom management", "learner-centred", "assessment", "continuous assessment", "practical", "scheme of work")
    low = _normalise(have_text)
    hits = [term for term in terms if term in low]
    ratio = len(hits) / len(terms)
    if ratio >= 0.50:
        return True, weight * min(1.0, 0.75 + ratio * 0.25), "; ".join(hits), f"Methodology evidence found: {', '.join(hits)}."
    if hits:
        return False, weight * ratio, "; ".join(hits), f"Limited methodology evidence found: {', '.join(hits)}."
    return False, 0.0, "", "No methodology or classroom-management evidence was found."


def _score_additional_skills(have_text, weight):
    terms = ("ict", "computer", "record keeping", "examination", "remedial", "group work", "scheme of work", "practical")
    low = _normalise(have_text)
    hits = [term for term in terms if term in low]
    ratio = len(hits) / len(terms)
    if not hits:
        return False, 0.0, "", "No additional relevant skills were found."
    return True, weight * min(1.0, 0.6 + ratio * 0.4), "; ".join(hits), f"Additional relevant skills: {', '.join(hits)}."


def _score_experience(profile, required, weight):
    """Experience criteria are stated as a number of years."""
    want_years = None
    match = re.search(r"(\d+(?:\.\d+)?)", str(required))
    if match:
        want_years = float(match.group(1))

    have_months = profile.total_experience_months
    if have_months is None:
        # Fall back to counting experience entries.
        entries = len(profile.by_type("experience"))
        if entries:
            have_months = entries * 12
            evidence = f"{entries} role(s) listed in the CV"
        else:
            evidence = ""
    else:
        years = have_months / 12
        evidence = f"CV states {years:.1f} years of experience"

    if want_years is None:
        # No target given: any documented experience counts.
        if have_months:
            return True, weight, evidence, "Relevant work experience is documented."
        return False, 0.0, "", "No work experience was found in the CV."

    have_years = (have_months or 0) / 12
    if have_years >= want_years:
        return True, weight, evidence, (
            f"Experience requirement met: {have_years:.1f} years against {want_years:g} required."
        )
    if have_years > 0:
        return False, weight * (have_years / want_years) * 0.9, evidence, (
            f"Partial experience: {have_years:.1f} years against {want_years:g} required."
        )
    return False, 0.0, "", f"No experience matching '{required}' was found in the CV."


def _dataset_category(label: str) -> str | None:
    low = _normalise(label)
    if "subject specialization" in low or "subject" in low:
        return "teaching subject specialization"
    if "professional teaching" in low or "teacher education" in low or "training" in low:
        return "professional teaching qualification/training"
    if "methodology" in low or "classroom" in low:
        return "teaching methodology and classroom management"
    if "additional" in low or "relevant skills" in low:
        return "additional relevant skills"
    if "academic" in low or "qualification" in low:
        return "academic qualification"
    if "experience" in low:
        return "teaching experience"
    return None


def _dataset_weight(label: str) -> float | None:
    category = _dataset_category(label)
    if category:
        return float(TRAINED_MODEL.get("criteria", {}).get(category, DATASET_CRITERIA.get(category)))
    return None


def _subject_from_text(text: str) -> set:
    low = _normalise(text)
    subjects = set()
    for subject, aliases in SUBJECT_ALIASES.items():
        if any(alias in low for alias in aliases):
            subjects.add(subject)
    return subjects


def _score_subject_specialization(profile, required, have_text, weight):
    candidate_subjects = _subject_from_text(have_text)
    wanted_text = _normalise(required)
    wanted_subjects = _subject_from_text(wanted_text)
    if not wanted_subjects:
        ratio = _match_ratio(required, _tokens(have_text), have_text)
    else:
        overlap = candidate_subjects & wanted_subjects
        ratio = 1.0 if overlap else 0.0
    evidence = _evidence_from(profile, required)
    if ratio >= 1.0:
        return True, weight, evidence, f"Teaching subject specialization is relevant to '{required}'."
    if ratio >= 0.6:
        return True, weight * ratio, evidence, f"Teaching subject is partially relevant to '{required}'."


def _load_trained_model():
    path = Path(__file__).with_name("trained_model.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


TRAINED_MODEL = _load_trained_model()


def _qualification_level(text: str) -> int:
    low = _normalise(text)
    for name, level in QUALIFICATION_LEVELS:
        if name in low:
            return level
    return 0
