# Running Tintin locally

This is the operational runbook for getting Tintin up on a workstation
(macOS or Linux). The remote sandbox can't run the real embedding model
(huggingface.co is blocked) or download IRS Pubs (irs.gov is blocked),
so production-quality runs happen here.

## Prerequisites

- Python 3.11+
- ~2 GB free disk (sentence-transformers model + ChromaDB + PDFs)
- An Anthropic API key
- Outbound HTTPS to `api.anthropic.com`, `huggingface.co`, and `www.irs.gov`

## 1. Install

```bash
git clone <repo> Tintin
cd Tintin
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

On Debian/Ubuntu systems where PyYAML is pre-installed by the OS:

```bash
pip install -e ".[dev]" --ignore-installed PyYAML
```

## 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and set:

- `ANTHROPIC_API_KEY` — required
- `TINTIN_DEFAULT_TAX_YEAR` — defaults to `2025`; bump at the start of each filing season
- `TINTIN_OIDC_CLIENT_ID` / `TINTIN_OIDC_CLIENT_SECRET` — only if you wire up SSO; the Streamlit UI works without them for local testing

Do **not** set `TINTIN_EMBEDDER=stub` for real use — that's a degraded
hash embedder for offline sandboxes only.

## 3. Populate the corpus

Six IRS Pubs are already in `corpus/irs_pubs/` (334, 463, 502, 505, 525, 936).
Fetch the remaining nine:

```bash
python scripts/download_pubs.py
```

This downloads 17, 501, 503, 535, 587, 590A, 590B, 596, 970 from
`www.irs.gov/pub/irs-pdf/pNNN.pdf` (the host-allowlist check is inlined
in the script so it can run before the rest of the package is built).
Pass specific Pub numbers as args to retry only those.

## 4. Ingest

```bash
mkdir -p data/chroma
python scripts/ingest.py corpus/irs_pubs/
```

First run downloads `sentence-transformers/all-MiniLM-L6-v2` (~90 MB) to
`~/.cache/huggingface`. Expect ~1k chunks per Pub. Subsequent ingests
reuse the cached model.

## 5. Run

Two processes — open two terminals (or use `tmux`):

```bash
# Terminal 1 — API
uvicorn app.api:app --host 127.0.0.1 --port 8000

# Terminal 2 — Streamlit UI
streamlit run app/main.py
```

Streamlit prints a `http://localhost:8501` URL. Open it, pick a tax year
in the dropdown, ask a question.

## 6. Smoke test without the UI

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'content-type: application/json' \
  -d '{
    "user_email": "you@firm.com",
    "question": "What is the standard mileage rate for business use of a car?",
    "tax_year": 2025
  }' | python -m json.tool
```

You should get a JSON response with `answer`, `bucket`, `pubs`,
`authority_block`, and `notes`.

## Troubleshooting

- **`OSError: We couldn't connect to 'https://huggingface.co'`** — your
  network blocks HuggingFace. Either allow it through, or pre-download
  the model on another machine and copy `~/.cache/huggingface/hub/` over.
- **`Failed building wheel for langdetect`** — `unstructured` isn't a
  dependency; if you see this, something else has re-introduced it.
- **`Multiple top-level packages discovered`** — the
  `[tool.setuptools.packages.find]` block in `pyproject.toml` is what
  prevents this; keep it.
- **403 from irs.gov in the download script** — irs.gov sometimes rate-
  limits aggressive clients; rerun specific Pubs with
  `python scripts/download_pubs.py 17 501` etc.

## Rolling forward at the start of a new filing season

1. Bump `TINTIN_DEFAULT_TAX_YEAR` in `.env`.
2. Re-run `python scripts/download_pubs.py` — overwriting old PDFs is
   fine, the ingest script picks up the new revision date from the
   first page.
3. Wipe the old index: `rm -rf data/chroma && mkdir -p data/chroma`.
4. Re-ingest: `python scripts/ingest.py corpus/irs_pubs/`.
5. Restart `uvicorn`.

Expect this to take 10-15 minutes end-to-end.
