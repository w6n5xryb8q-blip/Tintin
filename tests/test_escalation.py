import sqlite3
from pathlib import Path

import pytest

from app import authority
from app import config as config_module
from app import escalation


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "tintin.sqlite"
    monkeypatch.setattr(config_module.settings, "sqlite_path", db)
    monkeypatch.setattr(escalation.settings, "sqlite_path", db)
    yield db


def test_brief_renders_with_authority_chain():
    chain = authority.attach_authority("Pub 463")
    brief = escalation.build_brief(
        question_redacted="employee mileage reimbursement?",
        scope_reason="needs pro review on substantiation",
        retrieved_pubs=["463"],
        authority=chain,
        suggested_next_step="confirm strict §274(d) substantiation evidence is present",
    )
    rendered = brief.render()
    assert "Pub" in rendered
    assert "IRC §162" in rendered
    assert "Flowers" in rendered
    assert "suggested next step" in rendered.lower()


def test_brief_stored_to_sqlite(tmp_db: Path):
    brief = escalation.build_brief(
        question_redacted="q",
        scope_reason="state tax detected",
        retrieved_pubs=[],
        authority=None,
        suggested_next_step="route to state-tax desk",
    )
    escalation.store(brief)
    with sqlite3.connect(tmp_db) as c:
        rows = c.execute("SELECT id, scope_reason FROM escalations").fetchall()
    assert rows[0][0] == brief.id
    assert rows[0][1] == "state tax detected"
