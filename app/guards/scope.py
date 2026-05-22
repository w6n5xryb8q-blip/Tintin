from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ScopeOutcome(str, Enum):
    IN_SCOPE = "in_scope"
    STATE_TAX = "state_tax"
    RETURN_INTERPRETATION = "return_interpretation"
    PRIOR_YEAR_SPECIFIC = "prior_year_specific"
    INTERNATIONAL = "international"
    OFF_TOPIC = "off_topic"


@dataclass(frozen=True)
class ScopeDecision:
    outcome: ScopeOutcome
    reason: str

    @property
    def should_escalate(self) -> bool:
        return self.outcome is not ScopeOutcome.IN_SCOPE


_STATE_NAMES = (
    "alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|"
    "georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|"
    "maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|"
    "nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|"
    "ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|"
    "tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming"
)

_STATE_RE = re.compile(
    rf"\b(state (?:income )?tax|franchise tax|sales tax|use tax|nexus|"
    rf"(?:{_STATE_NAMES}) (?:state )?(?:income |sales |use )?tax)\b",
    re.IGNORECASE,
)
_RETURN_INTERP_RE = re.compile(
    r"\b(my client'?s? return|this return|form 1040 line|line \d+|"
    r"on line \d+|attached return|read this return|interpret this return)\b",
    re.IGNORECASE,
)
_PRIOR_YEAR_RE = re.compile(r"\b(tax year|TY|filing year)\s*(199\d|20[01]\d|202[0-3])\b", re.IGNORECASE)
_INTL_RE = re.compile(
    r"\b(GILTI|subpart f|treaty|FBAR|FATCA|PFIC|controlled foreign corporation|CFC|"
    r"transfer pricing|tax treaty)\b",
    re.IGNORECASE,
)
_INTL_ALLOWED_RE = re.compile(r"\b(FEIE|foreign earned income|ITIN|W-?7)\b", re.IGNORECASE)
# Stems allow suffixes (deduct → deduct, deduction, deductible, deducting).
# Stems use a leading \b but no trailing one. Be careful adding short stems:
# "tax" matches "taxable" and "taxpayer" (intended) but would also match
# "taxonomy" — accepted as a benign false-positive.
_TAX_STEMS = (
    "tax|deduct|credit|withhold|exempt|fil(?:e|ing|ed)|"
    "depreciat|amortiz|capital gain|dividend|"
    "itemiz|standard deduction|substantiat|reimburs|"
    "estimated payment|estimated tax|depend(?:ent|ant)|exemption|distribution|"
    # Everyday taxpayer phrasings.
    "claim|expense|write[-\\s]?off|gig|rideshare|side hustle|side gig|"
    "freelance|self.?employ|independent contractor|home office|"
    "business mile|business meal"
)

# Exact tokens — require full word boundary so "1040" doesn't match "10401".
_TAX_EXACT = (
    "IRS|1040|1099|W-?2|W-?7|IRA|401\\(?k\\)?|HSA|FSA|EITC|AOTC|LLC|"
    "ITIN|FEIE|RMD|publication|pub\\.?\\s*\\d|mileage|return|"
    "child tax credit"
)

_TAX_TOPIC_RE = re.compile(
    rf"\b(?:(?:{_TAX_STEMS})\w*|(?:{_TAX_EXACT})\b)",
    re.IGNORECASE,
)


def classify_scope(question: str) -> ScopeDecision:
    """Pure rules-layer classifier. The LLM-based classifier wraps this and only
    overrides the IN_SCOPE result — it cannot promote escalate-class decisions
    back into scope.
    """
    if _STATE_RE.search(question):
        return ScopeDecision(ScopeOutcome.STATE_TAX, "state/local tax detected")
    if _RETURN_INTERP_RE.search(question):
        return ScopeDecision(
            ScopeOutcome.RETURN_INTERPRETATION,
            "looks like reading or interpreting a specific return",
        )
    if _PRIOR_YEAR_RE.search(question):
        return ScopeDecision(
            ScopeOutcome.PRIOR_YEAR_SPECIFIC, "asks about a specific prior tax year"
        )
    if _INTL_RE.search(question) and not _INTL_ALLOWED_RE.search(question):
        return ScopeDecision(
            ScopeOutcome.INTERNATIONAL, "international/cross-border topic outside allowlist"
        )
    if not _TAX_TOPIC_RE.search(question):
        return ScopeDecision(ScopeOutcome.OFF_TOPIC, "no tax-topic signal detected")
    return ScopeDecision(ScopeOutcome.IN_SCOPE, "passes rules-layer scope check")
