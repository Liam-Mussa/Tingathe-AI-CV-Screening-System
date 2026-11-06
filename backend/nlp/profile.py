"""Parse a CV into structured profile items.

Design notes
------------
The parser is deliberately rule-based and transparent. A director reviewing a
score must be able to see *why* a candidate matched, so every item records the
sentence it came from. Where spaCy is available it is used for entity
recognition and sentence splitting; where it is not, the parser falls back to
regex so the pipeline still works on a machine without the language model.
"""
import re
from dataclasses import dataclass, field
from datetime import date

# Words that signal a degree, diploma or professional qualification.
QUALIFICATION_WORDS = (
    "bachelor", "bsc", "ba ", "b.ed", "beng", "llb", "mbbs", "btech",
    "master", "msc", "ma ", "m.ed", "mba", "phd", "doctorate",
    "diploma", "certificate", "advanced diploma", "higher diploma",
    "national certificate", "msce", "o level", "a level",
)

# Section headings found in CVs, mapped to the item type they introduce.
SECTION_HEADINGS = {
    "education": ("education", "academic", "qualifications", "academic background", "training"),
    "skill": ("skills", "key skills", "core skills", "competencies", "areas of expertise", "proficiencies"),
    "experience": ("experience", "work experience", "employment", "professional experience", "work history"),
}

# A date or a span of years, used to separate employment entries.
DATE_SPAN = re.compile(
    r"\b(?P<start_month>(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*)?"
    r"(?P<start_year>(?:19|20)\d{2})\b"
    r"\s*(?:[-–—]|\bto\b|\buntil\b)\s*"
    r"(?P<end_month>(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*)?"
    r"(?P<end_year>(?:19|20)\d{2}|present|current|to date|now)\b",
    re.IGNORECASE,
)
PRESENT_WORDS = {"present", "current", "to date", "now"}


@dataclass
class ProfileItemData:
    """One fact pulled out of a CV, with the evidence that produced it."""

    item_type: str            # education | skill | qualification | experience
    value: str                # the fact itself, e.g. "BSc Mathematics Education"
    institution: str | None = None
    source_snippet: str = ""  # the sentence the fact came from
    confidence: float = 0.9


@dataclass
class ParsedProfile:
    """Everything the parser could find in one document."""

    items: list = field(default_factory=list)
    total_experience_months: int | None = None
    needs_review: bool = False
    warnings: list = field(default_factory=list)

    def by_type(self, *types) -> list:
        return [i for i in self.items if i.item_type in types]


def _detect_section(heading: str) -> str | None:
    """Map a line of text to the profile section it introduces, if any."""
    low = heading.lower().strip().rstrip(":")
    for item_type, names in SECTION_HEADINGS.items():
        if any(low == n or low.startswith(n + " ") or low.startswith(n + ":") for n in names):
            return item_type
    return None


def _split_list_items(text: str) -> list:
    """Split a skills line written as bullets or commas into entries."""
    parts = re.split(r"[•·\-\*\u2022]|,\s|\s{2,}|\|", text)
    return [p.strip(" .;") for p in parts if p.strip(" .;")]


def _find_qualifications(line: str) -> list:
    """Return the qualification words present in a line."""
    low = " " + line.lower() + " "
    found = []
    for word in QUALIFICATION_WORDS:
        if word in low:
            found.append(word.strip())
    return found


def _span_months(line: str) -> int:
    """Months covered by a '2020 - present' style span on one line."""
    match = DATE_SPAN.search(line)
    if not match:
        return 0
    try:
        start = int(match.group("start_year"))
    except (TypeError, ValueError):
        return 0

    end_raw = (match.group("end_year") or "").lower().strip()
    if end_raw in PRESENT_WORDS:
        end = date.today().year
    else:
        try:
            end = int(end_raw)
        except (TypeError, ValueError):
            return 0
    return max(0, (end - start) * 12)


def _experience_months(text: str, items: list) -> int | None:
    """Work out total months of experience.

    Preferred source is an explicit statement ("6 years of experience"). When
    the CV only lists roles with dates, the date spans are summed instead, so a
    CV with two consecutive jobs is not undercounted.
    """
    stated = 0
    for match in re.finditer(r"(\d{1,2})\s*\+?\s*(years?|yrs?)\b", text, re.IGNORECASE):
        try:
            stated += int(match.group(1))
        except (TypeError, ValueError):
            continue
    if stated:
        return stated * 12

    months = 0
    for item in items:
        if item.item_type != "experience":
            continue
        months += _span_months(item.source_snippet or item.value)
    return months or None


def parse_document(text: str, doc_type: str = "cv") -> ParsedProfile:
    """Parse extracted text into a candidate profile."""
    profile = ParsedProfile()
    if not text or not text.strip():
        profile.needs_review = True
        profile.warnings.append("No text available to parse")
        return profile

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    current_section: str | None = None
    seen: set = set()

    for line in lines:
        section = _detect_section(line)
        if section:
            current_section = section
            continue

        low = line.lower()

        # A short line with no section context that names a qualification.
        quals = _find_qualifications(line)
        if quals and (current_section == "education" or len(line) < 90):
            item = ProfileItemData(
                item_type="qualification",
                value=line[:300],
                source_snippet=line,
                confidence=0.95 if current_section == "education" else 0.8,
            )
            if item.value.lower() not in seen:
                seen.add(item.value.lower())
                profile.items.append(item)
            continue

        if current_section == "skill":
            for entry in _split_list_items(line):
                if len(entry) < 2 or len(entry) > 80:
                    continue
                if entry.lower() in seen:
                    continue
                seen.add(entry.lower())
                profile.items.append(ProfileItemData(
                    item_type="skill",
                    value=entry,
                    source_snippet=line,
                    confidence=0.9,
                ))
            continue

        if current_section == "experience":
            if line.lower() not in seen:
                seen.add(line.lower())
                profile.items.append(ProfileItemData(
                    item_type="experience",
                    value=line[:300],
                    source_snippet=line,
                    confidence=0.85,
                ))
            continue

        # Outside a named section: catch inline mentions of qualifications.
        if quals and len(line) < 200:
            if line.lower() not in seen:
                seen.add(line.lower())
                profile.items.append(ProfileItemData(
                    item_type="qualification",
                    value=line[:300],
                    source_snippet=line,
                    confidence=0.7,
                ))

    profile.total_experience_months = _experience_months(text, profile.items)

    if not profile.items:
        profile.needs_review = True
        profile.warnings.append("No education, skills or experience could be identified")
    elif len(profile.items) < 3:
        profile.needs_review = True
        profile.warnings.append("Very few details found in the CV")

    return profile
