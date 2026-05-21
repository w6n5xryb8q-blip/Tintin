from __future__ import annotations

from app.config import settings

_RAW = {
    "app_title": "{{PUBLIC_NAME}} — tax research coach (internal)",
    "input_placeholder": "Ask a federal-tax research question. Don't paste client info.",
    "pii_rejected": (
        "I can't read that — it looks like it has client info (like an SSN, EIN, or account "
        "number). Please remove the personal details and try again."
    ),
    "scope_state": (
        "This looks like a state or local tax question. {{PUBLIC_NAME}} only covers federal IRS "
        "topics. I drafted a brief for a tax pro — tap 'Send to Tax Pro' to forward it."
    ),
    "scope_return": (
        "This sounds like reading a specific return. That always goes to a tax pro. "
        "Brief is ready — tap 'Send to Tax Pro'."
    ),
    "scope_offtopic": "That doesn't look like a tax question. Try rephrasing, or ask a tax pro.",
    "fetch_failed": (
        "I couldn't reach irs.gov to double-check this answer. The answer below comes from the "
        "local copy of the publication; please re-run when the network is back."
    ),
    "data_disclosure": (
        "Heads up: every question is logged for quality, with PII removed before saving. "
        "If you paste anything that looks like client info, {{PUBLIC_NAME}} will refuse it."
    ),
    "escalate_button": "Send to Tax Pro",
    "escalate_framing": "Good catch — this needs a pro. {{PUBLIC_NAME}} already drafted the brief for you.",
    "translate_tagalog": "Show this in Tagalog",
}


def t(key: str) -> str:
    return _RAW[key].replace("{{PUBLIC_NAME}}", settings.public_name)
