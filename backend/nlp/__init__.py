"""Turning raw document text into a structured candidate profile.

The extractors hand us plain text; the screening step needs facts it can match
against a vacancy's criteria. This module finds the education, skills,
qualifications and experience entries in a CV and returns them as
`ProfileItem`-shaped records, each carrying the sentence it came from so a
director can see the evidence behind any score.
"""
