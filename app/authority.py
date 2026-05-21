from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

from app.config import settings


@dataclass
class CaseRef:
    cite: str
    topic: str = ""


@dataclass
class AuthorityChain:
    pub_number: str
    irc: list[str] = field(default_factory=list)
    regs: list[str] = field(default_factory=list)
    rulings: list[str] = field(default_factory=list)
    cases: list[CaseRef] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.irc or self.regs or self.rulings or self.cases)


@dataclass
class CurrencyWarning:
    kind: str  # "irc_amended" | "reg_amended" | "pub_stale"
    detail: str


def _xref_path() -> Path:
    return settings.corpus_dir / "authority" / "xref.yaml"


@lru_cache(maxsize=1)
def _load_xref() -> dict:
    p = _xref_path()
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def reload_xref() -> None:
    """For tests / hot-reload."""
    _load_xref.cache_clear()


def _pub_key(pub_number: str) -> str:
    # Normalize "Pub 463", "Publication 463", "463", "Pub 590B" -> "pub_463" / "pub_590B".
    # Strip leading "pub"/"publication"/whitespace; keep the trailing alphanumeric
    # token (e.g. "590B") so 590A and 590B don't collide.
    import re

    s = pub_number.strip()
    s = re.sub(r"^(publication|pub\.?)\s*", "", s, flags=re.IGNORECASE)
    s = s.strip()
    if not s:
        return ""
    return f"pub_{s}"


def attach_authority(pub_number: str) -> AuthorityChain:
    xref = _load_xref()
    entry = xref.get(_pub_key(pub_number)) or {}
    return AuthorityChain(
        pub_number=pub_number,
        irc=[str(s) for s in (entry.get("irc", []) or [])],
        regs=[str(s) for s in (entry.get("regs", []) or [])],
        rulings=[str(s) for s in (entry.get("rulings", []) or [])],
        cases=[CaseRef(**c) if isinstance(c, dict) else CaseRef(cite=str(c)) for c in (entry.get("cases", []) or [])],
    )


def format_authority_block(chain: AuthorityChain) -> str:
    if chain.is_empty:
        return "Underlying authority: (none mapped for this publication — escalate before relying)"
    lines = ["Underlying authority:"]
    for sec in chain.irc:
        lines.append(f"  • IRC §{sec}")
    for reg in chain.regs:
        lines.append(f"  • Treas. Reg. §{reg}")
    for r in chain.rulings:
        lines.append(f"  • {r}")
    for c in chain.cases:
        topic = f" — {c.topic}" if c.topic else ""
        lines.append(f"  • {c.cite}{topic}")
    return "\n".join(lines)


def _parse_iso(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return date.fromisoformat(d)
    except ValueError:
        return None


def verify_authority_currency(
    chain: AuthorityChain,
    *,
    pub_revision_date: str | None,
    effective_dates: dict[str, str] | None = None,
) -> list[CurrencyWarning]:
    """Flag IRC/Reg amendments that post-date the cited Pub.

    `effective_dates` maps an authority key (e.g. "IRC 162", "Reg 1.274-5T")
    to an ISO date. In production this is populated from
    `corpus/authority/irc/*.yaml` and `corpus/authority/regs/*.yaml`. The function
    accepts an explicit dict so tests can inject without touching disk.
    """
    warnings: list[CurrencyWarning] = []
    pub_date = _parse_iso(pub_revision_date)
    eff = effective_dates or {}
    if pub_date is None:
        return warnings
    for sec in chain.irc:
        d = _parse_iso(eff.get(f"IRC {sec}"))
        if d and d > pub_date:
            warnings.append(
                CurrencyWarning(
                    "irc_amended",
                    f"IRC §{sec} was amended {d.isoformat()}, after the Pub's revision date ({pub_date.isoformat()}).",
                )
            )
    for reg in chain.regs:
        d = _parse_iso(eff.get(f"Reg {reg}"))
        if d and d > pub_date:
            warnings.append(
                CurrencyWarning(
                    "reg_amended",
                    f"Treas. Reg. §{reg} was amended {d.isoformat()}, after the Pub's revision date ({pub_date.isoformat()}).",
                )
            )
    return warnings
