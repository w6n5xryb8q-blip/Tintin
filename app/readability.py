from __future__ import annotations

from dataclasses import dataclass

import textstat

MAX_GRADE = 8.0


@dataclass
class ReadabilityResult:
    grade: float
    passed: bool


def score(text: str) -> ReadabilityResult:
    grade = float(textstat.flesch_kincaid_grade(text))
    return ReadabilityResult(grade=grade, passed=grade <= MAX_GRADE)
