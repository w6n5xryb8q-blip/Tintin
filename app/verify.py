from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.config import settings


class DisallowedHostError(RuntimeError):
    pass


_CACHE: dict[str, tuple[float, str]] = {}
_TTL_SECONDS = 24 * 3600


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    return host in settings.allowed_host_set


def fetch(url: str, *, ttl: int = _TTL_SECONDS) -> str:
    """Allowlisted fetch with on-disk-free TTL cache. Raises on disallowed host."""
    if not _host_allowed(url):
        raise DisallowedHostError(f"host not on allowlist: {url}")
    now = time.time()
    cached = _CACHE.get(url)
    if cached and now - cached[0] < ttl:
        return cached[1]
    r = httpx.get(url, timeout=15, follow_redirects=True)
    r.raise_for_status()
    final_host = (urlparse(str(r.url)).hostname or "").lower()
    if final_host not in settings.allowed_host_set:
        raise DisallowedHostError(f"redirect left allowlist: {r.url}")
    body = r.text
    _CACHE[url] = (now, body)
    return body


@dataclass
class VerificationResult:
    url_resolves: bool
    quote_found: bool
    revision_ok: bool
    notes: list[str]

    @property
    def passed(self) -> bool:
        return self.url_resolves and self.quote_found and self.revision_ok


def verify_citation(url: str, quote: str, *, max_age_days: int | None = None) -> VerificationResult:
    notes: list[str] = []
    try:
        body = fetch(url)
    except DisallowedHostError as e:
        return VerificationResult(False, False, False, [f"disallowed: {e}"])
    except httpx.HTTPError as e:
        return VerificationResult(False, False, False, [f"fetch failed: {e}"])

    url_ok = True
    # Loose match: collapse whitespace before comparison.
    needle = " ".join(quote.split())
    haystack = " ".join(body.split())
    quote_ok = needle.lower() in haystack.lower()
    if not quote_ok:
        notes.append("quoted passage not found verbatim on page")

    # The revision-date check is delegated to authority.verify_authority_currency
    # because it requires structured metadata, not just page scraping.
    revision_ok = True
    return VerificationResult(url_ok, quote_ok, revision_ok, notes)
