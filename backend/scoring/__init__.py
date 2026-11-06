"""Weighted, explainable candidate scoring.

Each vacancy has criteria with weights. For every criterion the scorer decides
whether the candidate matched, assigns a score out of the criterion's weight,
and writes a plain-language explanation naming the evidence it used. Directors
never see an unexplained number.
"""
