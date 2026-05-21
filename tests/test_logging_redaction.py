import re
import sqlite3
from pathlib import Path

import pytest

from app import config as config_module
from app.logging import store


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "tintin.sqlite"
    monkeypatch.setattr(config_module.settings, "sqlite_path", db)
    # also reflect into store module's cached settings reference
    monkeypatch.setattr(store.settings, "sqlite_path", db)
    yield db


def test_pii_redacted_before_write(tmp_db: Path):
    store.log_turn(
        user_email="anna@firm.example",
        question="client SSN 123-45-6789 needs to know about pub 463",
        category="463",
        retrieved_pubs=["463"],
        confidence_bucket="Solid",
        escalated=False,
        brief_id=None,
    )
    with sqlite3.connect(tmp_db) as c:
        rows = c.execute("SELECT question_redacted, user_email_hash FROM turns").fetchall()
    assert rows
    q, email_hash = rows[0]
    assert "123-45-6789" not in q
    assert "[REDACTED-SSN]" in q
    assert not re.fullmatch(r".*@.*", email_hash)  # email itself is hashed
