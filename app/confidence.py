from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Bucket(str, Enum):
    SOLID = "Solid"
    MOSTLY_SOLID = "Mostly solid — double-check the flagged detail"
    USE_WITH_CAUTION = "Use with caution"
    ESCALATE = "Escalate"


@dataclass
class ConfidenceSignals:
    retrieval_score: float  # 0..1, top-k similarity
    quote_grounded: bool  # cited quote present in cited Pub
    self_consistency: float  # 0..1, agreement across N samples
    currency_ok: bool  # Pub revision within window AND no later IRC/Reg amendment
    hard_escalate: bool = False  # scope router or PII guard fired
    authority_concordance_ok: bool = True  # no flagged authority currency warnings
    reasons: list[str] = field(default_factory=list)


def bucket_for(s: ConfidenceSignals) -> tuple[Bucket, str]:
    if s.hard_escalate:
        return Bucket.ESCALATE, "scope/guard rule triggered"
    if not s.authority_concordance_ok:
        return Bucket.USE_WITH_CAUTION, "underlying authority changed after the Pub's revision date"
    if not s.currency_ok:
        return Bucket.USE_WITH_CAUTION, "cited publication may be stale"
    if not s.quote_grounded:
        return Bucket.USE_WITH_CAUTION, "could not verify the quote against the publication"
    if s.retrieval_score >= 0.75 and s.self_consistency >= 0.8:
        return Bucket.SOLID, "strong retrieval + consistent across samples"
    if s.retrieval_score >= 0.6 and s.self_consistency >= 0.6:
        return Bucket.MOSTLY_SOLID, "moderate retrieval or mild sample disagreement"
    return Bucket.USE_WITH_CAUTION, "weak retrieval or sample disagreement"
