from __future__ import annotations

import re
from dataclasses import dataclass

# SSN: 3-2-4. NO validity exclusions — redact anything SSN-shaped.
# An earlier version skipped area 000/666/9xx, group 00, and serial 0000
# on the theory that real SSA-issued numbers never use those ranges. But
# clients send typo'd, fake, training, or reserved SSNs ("My SSN is
# 400-00-6001..." — area 400 with group 00 is in the SSA's reserved
# fictitious-number block); under the validity policy that string sailed
# straight through redact() into the escalation brief. PII guards must
# optimize for recall: redact anything that looks like the thing.
_SSN = re.compile(r"(?<!\d)\d{3}[- ]\d{2}[- ]\d{4}(?!\d)")
# EIN: 2-7
_EIN = re.compile(r"(?<!\d)\d{2}-\d{7}(?!\d)")
# ITIN: 9XX-(70-88|90-92|94-99)-XXXX. Because the relaxed _SSN now also
# matches the 9XX shape, _ITIN must run BEFORE _SSN in _PATTERNS so the
# more specific kind wins classification (both still get redacted).
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


# Order matters: more specific kinds first so they claim spans before less
# specific kinds get to look at them. ITIN is a strict subset of the SSN
# shape, so itin > ssn. credit_card (groups-of-four) is a stricter shape
# than bank_account (raw 8-17 digits), so credit_card > bank_account.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("itin", _ITIN),
    ("ssn", _SSN),
    ("ein", _EIN),
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
