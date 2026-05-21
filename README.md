# Tintin (internal codename)

> **TODO: choose public name before any external surface ships.**
> "Tintin" is a registered trademark of Moulinsart/Hergé; this name is used only as an internal codename in the repo. UI copy reads from `app/ui/strings.py` and substitutes `{{PUBLIC_NAME}}` at render time.

A local-sourced tax-research coach for CPA-firm admin staff. Grounds every answer in a local library of IRS publications, verifies currency against `irs.gov`, cross-references the underlying IRC sections / Treasury Regs / Revenue Rulings / case law, speaks at CEFR B1–B2, and routes any client-specific or out-of-scope question to a tax professional with a pre-drafted escalation brief.

**Not legal or tax advice.** IRS Publications are not legal authority. The underlying authority (IRC, Treasury Regs, Rev. Ruls., case law) is surfaced beside every Pub citation so a reviewing tax pro can trace the breadcrumb. Plain-language summaries always come from the Publication, never invented from the statute.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # fill in ANTHROPIC_API_KEY and OIDC creds

# Drop IRS publication PDFs into corpus/irs_pubs/
python scripts/ingest.py corpus/irs_pubs/

# Run the golden-question eval
python scripts/eval.py tests/golden/questions.yaml

# Launch the UI
streamlit run app/main.py
```

## Architecture (one line each)

- `app/guards/` — PII reject, prompt-injection sanitization, scope router.
- `app/retriever.py` — ChromaDB over local IRS pub corpus.
- `app/llm.py` — pluggable provider (Anthropic default; Ollama stub).
- `app/verify.py` — host-allowlisted live fetch (`irs.gov`, `uscode.house.gov`, `ecfr.gov`).
- `app/authority.py` — joins each Pub citation to its IRC / Reg / Ruling / case chain via `corpus/authority/xref.yaml`.
- `app/confidence.py` — deterministic 4-bucket label from signals (no fake percentage).
- `app/readability.py` — Flesch-Kincaid ≤ 8 linter with regenerate loop.
- `app/escalation.py` — structured brief with likely controlling authority.
- `app/logging/` — SQLite store; PII redacted *at write time*.

## Data-handling disclosure (shown on first run)

- Email-based SSO is required.
- Every question is logged with PII **redacted before write** (SSNs, EINs, account numbers, names matched by NER).
- Pasted client data is rejected at the input guard; nothing client-identifying lands on disk raw.
- Logs are used only to measure escalation quality and to improve the golden-question set.

## Branch

Active branch: `claude/local-sourced-chatbot-fTbe5`.
