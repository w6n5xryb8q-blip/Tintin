from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import authority, confidence, escalation, readability, retriever
from app.config import settings
from app.guards import classify_scope, detect_pii, redact, sanitize_for_prompt
from app.guards.scope import ScopeOutcome
from app.llm import get_provider
from app.logging import log_turn
from app.ui.strings import t

app = FastAPI(title="Tintin API")

_PROMPTS = Path(__file__).parent / "prompts"


class AskIn(BaseModel):
    user_email: str
    question: str
    tax_year: int | None = None


class AskOut(BaseModel):
    answer: str | None
    bucket: str
    reason: str
    pubs: list[str]
    authority_block: str
    escalated: bool
    brief: str | None
    notes: list[str]


def _system_prompt() -> str:
    return (_PROMPTS / "system.md").read_text().replace("{{PUBLIC_NAME}}", settings.public_name)


def _answer_prompt(
    retrieved_context: str, authority_candidates: str, user_block: str, tax_year: int
) -> str:
    tmpl = (_PROMPTS / "answer.md").read_text()
    return tmpl.format(
        retrieved_context=retrieved_context,
        authority_candidates=authority_candidates,
        user_block=user_block,
        tax_year=tax_year,
    )


def _tax_year_mismatch(chunks, tax_year: int) -> str | None:
    """Return a note string if the top chunk's revision_date doesn't match the requested TY.

    The ingest pipeline stamps "TYNNNN" for Pubs whose first page says
    "For use in preparing NNNN Returns". Other revision-date formats
    (e.g. "March 2024") get a pass — we can't compare them to a TY cleanly.
    """
    if not chunks:
        return None
    rev = (chunks[0].revision_date or "").strip()
    if not rev.upper().startswith("TY"):
        return None
    try:
        pub_ty = int(rev[2:])
    except ValueError:
        return None
    if pub_ty == tax_year:
        return None
    return (
        f"Top match is Pub {chunks[0].pub_number} for TY{pub_ty}, "
        f"but you selected TY{tax_year}. Rules may have changed — verify before relying."
    )


def _retrieved_to_context(chunks) -> tuple[str, list[str]]:
    lines = []
    pubs: list[str] = []
    for c in chunks:
        pub = c.pub_number
        if pub and pub not in pubs:
            pubs.append(pub)
        lines.append(
            f"[Pub {pub} · {c.section} · revised {c.revision_date} · score {c.score:.2f}]\n{c.text}"
        )
    return "\n\n---\n\n".join(lines), pubs


def _escalate(
    *, user_email: str, question_redacted: str, reason: str, pubs: list[str]
) -> tuple[str, str]:
    chain = authority.attach_authority(pubs[0]) if pubs else None
    brief = escalation.build_brief(
        question_redacted=question_redacted,
        scope_reason=reason,
        retrieved_pubs=pubs,
        authority=chain,
        suggested_next_step="Verify the controlling authority above against the client's facts.",
    )
    escalation.store(brief)
    log_turn(
        user_email=user_email,
        question=question_redacted,
        category=None,
        retrieved_pubs=pubs,
        confidence_bucket=confidence.Bucket.ESCALATE.value,
        escalated=True,
        brief_id=brief.id,
    )
    return brief.id, brief.render()


@app.post("/ask", response_model=AskOut)
def ask(body: AskIn) -> AskOut:
    if not body.question.strip():
        raise HTTPException(400, "empty question")

    # 1. PII guard — hard reject raw client data.
    findings = detect_pii(body.question)
    if findings:
        return AskOut(
            answer=None,
            bucket=confidence.Bucket.ESCALATE.value,
            reason="pii_rejected",
            pubs=[],
            authority_block="",
            escalated=False,
            brief=None,
            notes=[t("pii_rejected")],
        )

    question_redacted = redact(body.question, findings)

    # 2. Scope guard.
    scope = classify_scope(body.question)
    scope_rescued_pub: str | None = None
    if scope.outcome is not ScopeOutcome.IN_SCOPE:
        # Retrieve anyway to attach Pubs/authority to the brief.
        chunks = retriever.query(body.question, k=4)
        _, pubs = _retrieved_to_context(chunks)

        # Retrieval-rescue: only OFF_TOPIC false-negatives get rescued.
        # STATE_TAX / RETURN_INTERPRETATION / INTERNATIONAL / PRIOR_YEAR
        # are deliberate refusals — strong retrieval doesn't override them.
        if (
            scope.outcome is ScopeOutcome.OFF_TOPIC
            and chunks
            and chunks[0].score >= settings.scope_rescue_min_score
        ):
            scope_rescued_pub = chunks[0].pub_number or ""
        else:
            brief_id, rendered = _escalate(
                user_email=body.user_email,
                question_redacted=question_redacted,
                reason=scope.reason,
                pubs=pubs,
            )
            key = {
                ScopeOutcome.STATE_TAX: "scope_state",
                ScopeOutcome.RETURN_INTERPRETATION: "scope_return",
            }.get(scope.outcome, "scope_offtopic")
            return AskOut(
                answer=None,
                bucket=confidence.Bucket.ESCALATE.value,
                reason=scope.reason,
                pubs=pubs,
                authority_block=authority.format_authority_block(
                    authority.attach_authority(pubs[0]) if pubs else authority.AuthorityChain("")
                ),
                escalated=True,
                brief=rendered,
                notes=[t(key)],
            )

    # 3. Retrieve.
    chunks = retriever.query(body.question, k=6)
    retrieved_context, pubs = _retrieved_to_context(chunks)
    if not chunks:
        brief_id, rendered = _escalate(
            user_email=body.user_email,
            question_redacted=question_redacted,
            reason="retrieval returned no matches",
            pubs=[],
        )
        return AskOut(
            answer=None,
            bucket=confidence.Bucket.ESCALATE.value,
            reason="no retrieval matches",
            pubs=[],
            authority_block="",
            escalated=True,
            brief=rendered,
            notes=["no matching publication in the local corpus"],
        )

    # 4. Authority candidates for the top Pub.
    top_chain = authority.attach_authority(pubs[0])
    authority_candidates = authority.format_authority_block(top_chain)

    # 5. LLM.
    tax_year = body.tax_year or settings.default_tax_year
    user_block = sanitize_for_prompt(body.question)
    prompt = _answer_prompt(retrieved_context, authority_candidates, user_block, tax_year)
    provider = get_provider()
    resp = provider.complete(system=_system_prompt(), user=prompt, temperature=0.3)
    answer = resp.text

    # 6. Readability lint with one regenerate.
    r = readability.score(answer)
    if not r.passed:
        resp2 = provider.complete(
            system=_system_prompt(),
            user=prompt + "\n\nThe previous answer was too complex. Rewrite at CEFR B1–B2 (Flesch-Kincaid ≤ 8). Shorter sentences. Same content.",
            temperature=0.3,
        )
        answer = resp2.text
        r = readability.score(answer)

    # 7. Confidence signals.
    quote_ok = any(chunk.text[:60].strip() in answer for chunk in chunks[:2])
    top_score = chunks[0].score
    currency_warnings = authority.verify_authority_currency(
        top_chain, pub_revision_date=chunks[0].revision_date or None
    )
    signals = confidence.ConfidenceSignals(
        retrieval_score=top_score,
        quote_grounded=quote_ok,
        self_consistency=1.0,  # single-sample MVP; sampling loop is a TODO.
        currency_ok=True,
        authority_concordance_ok=not currency_warnings,
    )
    bucket, reason = confidence.bucket_for(signals)

    log_turn(
        user_email=body.user_email,
        question=question_redacted,
        category=pubs[0] if pubs else None,
        retrieved_pubs=pubs,
        confidence_bucket=bucket.value,
        escalated=False,
        brief_id=None,
    )

    notes = [w.detail for w in currency_warnings]
    ty_note = _tax_year_mismatch(chunks, tax_year)
    if ty_note:
        notes.append(ty_note)
    if not r.passed:
        notes.append(f"readability still above target (grade {r.grade:.1f})")

    if scope_rescued_pub is not None:
        # Cap confidence — the scope guard's false-negative is itself a
        # signal that the question was phrased ambiguously.
        if bucket is confidence.Bucket.SOLID or bucket is confidence.Bucket.MOSTLY_SOLID:
            bucket = confidence.Bucket.USE_WITH_CAUTION
            reason = "scope guard initially flagged this as off-topic"
        notes.insert(
            0,
            f"Scope guard initially flagged this as off-topic, but retrieval "
            f"found a strong match in Pub {scope_rescued_pub}. Verify before relying.",
        )

    return AskOut(
        answer=answer,
        bucket=bucket.value,
        reason=reason,
        pubs=pubs,
        authority_block=authority_candidates,
        escalated=False,
        brief=None,
        notes=notes,
    )
