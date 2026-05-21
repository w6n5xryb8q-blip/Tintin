"""Download IRS publication PDFs into corpus/irs_pubs/.

Uses the canonical irs.gov URL pattern: https://www.irs.gov/pub/irs-pdf/pNNN.pdf
Goes through `app.verify.fetch_pdf`, which enforces the allowlist (irs.gov only).

Usage:
    python scripts/download_pubs.py            # downloads PUBS list below
    python scripts/download_pubs.py 17 501     # downloads only specified pubs
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

from app.verify import DisallowedHostError, _host_allowed
from app.config import settings

# Core v1 corpus. Names match the xref keys (so "590A" stays distinct from "590B").
PUBS = [
    "17",     # Your Federal Income Tax (Individuals)
    "334",    # Tax Guide for Small Business
    "463",    # Travel, Gift, and Car Expenses
    "501",    # Dependents, Standard Deduction, and Filing Information
    "502",    # Medical and Dental Expenses
    "503",    # Child and Dependent Care Expenses
    "505",    # Tax Withholding and Estimated Tax
    "525",    # Taxable and Nontaxable Income
    "535",    # Business Expenses
    "587",    # Business Use of Your Home
    "590A",   # Contributions to IRAs
    "590B",   # Distributions from IRAs
    "596",    # Earned Income Credit
    "936",    # Home Mortgage Interest Deduction
    "970",    # Tax Benefits for Education
]


def pub_url(num: str) -> str:
    # The IRS uses lower-case suffix in the PDF path (e.g. p590a.pdf, p590b.pdf).
    return f"https://www.irs.gov/pub/irs-pdf/p{num.lower()}.pdf"


def download(num: str, dest_dir: Path) -> Path:
    url = pub_url(num)
    if not _host_allowed(url):
        raise DisallowedHostError(f"refusing non-allowlisted url: {url}")
    dest = dest_dir / f"p{num}.pdf"
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip (already present): {dest.name}")
        return dest
    print(f"  fetching {url} ...")
    with httpx.stream("GET", url, timeout=60, follow_redirects=True) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    print(f"  wrote {dest.name} ({dest.stat().st_size // 1024} KB)")
    return dest


def main(argv: list[str]) -> int:
    requested = argv[1:] if len(argv) > 1 else PUBS
    dest_dir = settings.corpus_dir / "irs_pubs"
    dest_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for num in requested:
        try:
            download(num, dest_dir)
        except (httpx.HTTPError, DisallowedHostError) as e:
            failures.append(f"{num}: {e}")
            print(f"  ! failed {num}: {e}", file=sys.stderr)
    if failures:
        print(f"\n{len(failures)} failure(s); rerun specific pubs to retry.", file=sys.stderr)
        return 1
    print("\nAll requested PDFs present. Next: python scripts/ingest.py corpus/irs_pubs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
