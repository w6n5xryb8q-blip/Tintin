from __future__ import annotations

GLOSSARY: dict[str, str] = {
    "AGI": "Adjusted Gross Income — your total income minus a few specific subtractions.",
    "AOTC": "American Opportunity Tax Credit — a tax credit for the first 4 years of college.",
    "EITC": "Earned Income Tax Credit — a refundable credit for lower-income workers.",
    "FEIE": "Foreign Earned Income Exclusion — lets US workers abroad exclude some foreign pay.",
    "ITIN": "Individual Taxpayer Identification Number — a tax ID for people who can't get an SSN.",
    "LLC (credit)": "Lifetime Learning Credit — a tax credit for continuing education.",
    "MAGI": "Modified Adjusted Gross Income — AGI with a few items added back.",
    "SE tax": "Self-Employment tax — Social Security + Medicare tax for self-employed people.",
    "pro rata": "Split in proportion. Example: half the year = half the deduction.",
    "de minimis": "Too small to bother with — the rule doesn't apply if the amount is tiny.",
}


def gloss(term: str) -> str | None:
    return GLOSSARY.get(term)
