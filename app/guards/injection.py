from __future__ import annotations

import re

_INJECTION_PHRASES = (
    r"ignore (?:all |the |your |previous |above )+instructions?",
    r"disregard (?:all |the |your |previous |above )+instructions?",
    r"forget (?:everything|all|the prompt)",
    r"you are now",
    r"new instructions?:",
    r"system\s*:\s*",
    r"</?\s*system\s*>",
    r"</?\s*assistant\s*>",
    r"act as (?:a|an) ",
    r"reveal (?:your |the )?(?:system )?prompt",
    r"print (?:your |the )?(?:system )?prompt",
)
_INJECTION_RE = re.compile("|".join(_INJECTION_PHRASES), re.IGNORECASE)


def detect_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text))


def sanitize_for_prompt(user_text: str) -> str:
    """Wrap user-supplied content so the model treats it as data, not instructions.

    The wrapper plus the system-prompt instruction to ignore directives inside
    <user_content> is the content-isolation pattern. We also strip closing
    sentinels from the body so the user cannot escape the wrapper.
    """
    body = user_text.replace("</user_content>", "</user_content_escaped>")
    return f"<user_content>\n{body}\n</user_content>"
