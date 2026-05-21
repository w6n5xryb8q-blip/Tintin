from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone

from app.config import settings
from app.guards.pii import detect_pii, redact


def _conn() -> sqlite3.Connection:
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(settings.sqlite_path)


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                user_email_hash TEXT NOT NULL,
                question_redacted TEXT NOT NULL,
                category TEXT,
                retrieved_pubs TEXT,
                confidence_bucket TEXT,
                escalated INTEGER NOT NULL DEFAULT 0,
                brief_id TEXT
            )
            """
        )


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def log_turn(
    *,
    user_email: str,
    question: str,
    category: str | None,
    retrieved_pubs: list[str],
    confidence_bucket: str | None,
    escalated: bool,
    brief_id: str | None,
) -> None:
    # Redact PII *at write time* so raw PII never lands on disk.
    findings = detect_pii(question)
    question_redacted = redact(question, findings)
    init_db()
    with _conn() as c:
        c.execute(
            "INSERT INTO turns (ts, user_email_hash, question_redacted, category, "
            "retrieved_pubs, confidence_bucket, escalated, brief_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                _hash_email(user_email),
                question_redacted,
                category,
                ",".join(retrieved_pubs),
                confidence_bucket,
                1 if escalated else 0,
                brief_id,
            ),
        )
