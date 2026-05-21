"""Ingest IRS publication PDFs into the local Chroma collection.

Usage:
    python scripts/ingest.py corpus/irs_pubs/

Each PDF should be named like `p17.pdf`, `p463.pdf`, etc. Revision date is
parsed from the first page if present (regex on "Revised: Month YYYY" or
"For use in preparing YYYY Returns"); otherwise marked "unknown".
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from pypdf import PdfReader

from app import retriever

_REVISED_RE = re.compile(r"Revised:?\s*([A-Z][a-z]+\s+\d{4})", re.IGNORECASE)
_USE_IN_RE = re.compile(r"For use in preparing\s+(\d{4})\s+Returns", re.IGNORECASE)
_SECTION_RE = re.compile(r"^\s*(?:Chapter|Section|Part)\s+\d+[.: ]?\s*(.+)$", re.MULTILINE)


def _pub_number(path: Path) -> str:
    stem = path.stem.lower()
    m = re.match(r"p(?:ub)?(\d+)", stem)
    return m.group(1) if m else stem


def _revision_date(text: str) -> str:
    m = _REVISED_RE.search(text)
    if m:
        return m.group(1)
    m = _USE_IN_RE.search(text)
    if m:
        return f"TY{m.group(1)}"
    return "unknown"


def _chunk(text: str, *, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    chunks: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(n, i + max_chars)
        # Try to break on a paragraph boundary.
        if end < n:
            nl = text.rfind("\n\n", i, end)
            if nl > i + max_chars // 2:
                end = nl
        chunks.append(text[i:end].strip())
        if end == n:
            break
        i = max(end - overlap, i + 1)
    return [c for c in chunks if c]


def ingest_pdf(path: Path) -> int:
    reader = PdfReader(str(path))
    full = "\n".join(p.extract_text() or "" for p in reader.pages)
    pub = _pub_number(path)
    revised = _revision_date(full)
    source_url = f"https://www.irs.gov/pub/irs-pdf/p{pub}.pdf"

    pieces = _chunk(full)
    records = []
    for idx, piece in enumerate(pieces):
        # Best-effort section label from the chunk's first heading-like line.
        first_line = next((ln.strip() for ln in piece.splitlines() if ln.strip()), "")
        section = first_line[:120]
        records.append(
            {
                "id": hashlib.sha1(f"{pub}:{idx}:{piece[:64]}".encode()).hexdigest(),
                "text": piece,
                "metadata": {
                    "pub_number": pub,
                    "section": section,
                    "revision_date": revised,
                    "source_url": source_url,
                },
            }
        )
    retriever.add_chunks(records)
    return len(records)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    root = Path(argv[1])
    if not root.exists():
        print(f"no such directory: {root}", file=sys.stderr)
        return 2
    pdfs = sorted(root.glob("*.pdf"))
    if not pdfs:
        print(f"no PDFs in {root}", file=sys.stderr)
        return 1
    total = 0
    for p in pdfs:
        n = ingest_pdf(p)
        total += n
        print(f"  ingested {p.name}: {n} chunks")
    print(f"done — {total} chunks across {len(pdfs)} publications")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
