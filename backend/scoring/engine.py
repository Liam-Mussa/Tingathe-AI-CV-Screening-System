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
import re
from dataclasses import dataclass, field

# Words that add nothing when matching a skill or qualification.
STOP_WORDS = {
    "and", "or", "the", "a", "an", "of", "in", "with", "for", "to", "at",
    "on", "by", "from", "experience", "skills", "knowledge", "ability",
    "proficiency", "understanding", "strong", "good", "excellent", "demonstrated",
}


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
    scoring_version: str = "v1"


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

        if ctype == "experience":
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
    best_ratio = 0.0
    best_item = None
    for item in quals:
        item_tokens = _tokens(f"{item.value} {getattr(item, 'institution', None) or ''}")
        ratio = _match_ratio(required, item_tokens, _normalise(item.value))
        if ratio > best_ratio:
            best_ratio = ratio
            best_item = item

    if best_ratio >= 0.6:
        evidence = best_item.source_snippet or best_item.value if best_item else ""
        return True, weight, evidence, f"Qualification met: '{required}' is listed in the CV."
    if best_ratio > 0:
        evidence = best_item.source_snippet or best_item.value if best_item else ""
        return False, weight * 0.5, evidence, (
            f"Partial match: the CV mentions a related qualification but not '{required}'."
        )
    return False, 0.0, "", f"No qualification matching '{required}' was found in the CV."


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
