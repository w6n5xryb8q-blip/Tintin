from __future__ import annotations

import re
from dataclasses import dataclass

# SSN: 3-2-4 with conservative exclusions (no 000/666/9xx area, no 00 group, no 0000 serial).
_SSN = re.compile(
    r"(?<!\d)(?!000|666|9\d{2})\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}(?!\d)"
)
# EIN: 2-7
_EIN = re.compile(r"(?<!\d)\d{2}-\d{7}(?!\d)")
# ITIN: 9XX-(70-88|90-92|94-99)-XXXX
_ITIN = re.compile(r"(?<!\d)9\d{2}-(7\d|8[0-8]|9[0-24-9])-\d{4}(?!\d)")
# US bank-account-ish: 8-17 contiguous digits (heuristic; high-recall, will false-positive — by design)
_BANK = re.compile(r"(?<!\d)\d{8,17}(?!\d)")
# Routing number: 9 digits — same heuristic class, covered by _BANK above when ≥ 8.
# Credit card: 13-19 contiguous digits, optionally space/dash separated in groups of 4.
_CC = re.compile(r"(?<!\d)(?:\d{4}[- ]?){3,4}\d{1,4}(?!\d)")


@dataclass(frozen=True)
class PIIFinding:
    kind: str
    value: str
    start: int
    end: int


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ssn", _SSN),
    ("ein", _EIN),
    ("itin", _ITIN),
    ("credit_card", _CC),
    ("bank_account", _BANK),
)


def detect_pii(text: str) -> list[PIIFinding]:
    findings: list[PIIFinding] = []
    seen_spans: list[tuple[int, int]] = []
    for kind, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            # Skip if this span is inside a span already claimed by a more specific pattern.
            if any(s <= span[0] and span[1] <= e for s, e in seen_spans):
                continue
            findings.append(PIIFinding(kind=kind, value=m.group(0), start=span[0], end=span[1]))
            seen_spans.append(span)
    return findings


def redact(text: str, findings: list[PIIFinding] | None = None) -> str:
    findings = findings if findings is not None else detect_pii(text)
    if not findings:
        return text
    # Apply replacements right-to-left so indices stay valid.
    out = text
    for f in sorted(findings, key=lambda x: x.start, reverse=True):
        out = out[: f.start] + f"[REDACTED-{f.kind.upper()}]" + out[f.end :]
    return out
