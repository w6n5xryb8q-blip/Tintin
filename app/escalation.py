from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.authority import AuthorityChain, format_authority_block
from app.config import settings


@dataclass
class EscalationBrief:
    id: str
    question_redacted: str
    scope_reason: str
    retrieved_pubs: list[str]
    authority: AuthorityChain | None
    suggested_next_step: str
    pii_kinds_redacted: tuple[str, ...] = ()

    def _question_header(self) -> str:
        if not self.pii_kinds_redacted:
            return "Question:"
        kinds = ", ".join(sorted(k.upper() for k in self.pii_kinds_redacted))
        return f"Question (redacted: {kinds}):"

    def render(self) -> str:
        pubs = ", ".join(self.retrieved_pubs) if self.retrieved_pubs else "(none)"
        auth = format_authority_block(self.authority) if self.authority else "Underlying authority: (none mapped)"
        return (
            "Tax-pro escalation brief\n"
            "------------------------\n"
            f"{self._question_header()}\n  {self.question_redacted}\n\n"
            f"Why this was escalated:\n  {self.scope_reason}\n\n"
            f"What was found:\n  Pubs touched: {pubs}\n\n"
            f"Likely controlling authority:\n  {auth}\n\n"
            f"Suggested next step:\n  {self.suggested_next_step}\n"
        )


def _conn() -> sqlite3.Connection:
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(settings.sqlite_path)


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS escalations (
                id TEXT PRIMARY KEY,
                ts TEXT NOT NULL,
                question_redacted TEXT NOT NULL,
                scope_reason TEXT NOT NULL,
                retrieved_pubs TEXT NOT NULL,
                authority_json TEXT,
                suggested_next_step TEXT NOT NULL,
                rendered TEXT NOT NULL
            )
            """
        )


def build_brief(
    *,
    question_redacted: str,
    scope_reason: str,
    retrieved_pubs: list[str],
    authority: AuthorityChain | None,
    suggested_next_step: str,
    pii_kinds_redacted: tuple[str, ...] = (),
) -> EscalationBrief:
    return EscalationBrief(
        id=str(uuid.uuid4()),
        question_redacted=question_redacted,
        scope_reason=scope_reason,
        retrieved_pubs=retrieved_pubs,
        authority=authority,
        suggested_next_step=suggested_next_step,
        pii_kinds_redacted=pii_kinds_redacted,
    )


def store(brief: EscalationBrief) -> None:
    init_db()
    import json

    auth_json = None
    if brief.authority:
        auth_json = json.dumps(
            {
                "pub_number": brief.authority.pub_number,
                "irc": brief.authority.irc,
                "regs": brief.authority.regs,
                "rulings": brief.authority.rulings,
                "cases": [{"cite": c.cite, "topic": c.topic} for c in brief.authority.cases],
            }
        )
    with _conn() as c:
        c.execute(
            "INSERT INTO escalations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                brief.id,
                datetime.now(timezone.utc).isoformat(),
                brief.question_redacted,
                brief.scope_reason,
                ",".join(brief.retrieved_pubs),
                auth_json,
                brief.suggested_next_step,
                brief.render(),
            ),
        )
