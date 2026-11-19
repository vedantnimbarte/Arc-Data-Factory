"""Pure compliance logic: PII redaction, license allow-list, secret detection.

PII is redacted in place rather than rejecting the document — one email in a
README should not drop the file. Leaked secrets and disallowed licenses still
reject. Pattern-based on purpose: NER-based detectors flag names, dates and
URLs everywhere in code, and are seconds-per-doc slow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_PII_PATTERNS = {
    # (?!git@) keeps SSH clone URLs like git@github.com:owner/repo intact.
    "EMAIL_ADDRESS": re.compile(
        r"(?<![\w.+-])(?!git@)[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b"
    ),
    "US_SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b"),
    # Separators required so bare numeric constants in code aren't treated as phones.
    "PHONE_NUMBER": re.compile(r"(?<![\w-])(?:\+\d{1,3}[ .-])?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b"),
}

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),  # Slack
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),  # Google API key
    re.compile(r"\bsk_live_[0-9A-Za-z]{24,}\b"),  # Stripe
    re.compile(r"\bsk-(?:ant|proj)-[A-Za-z0-9_-]{20,}"),  # Anthropic / OpenAI
)

# Permissive licenses acceptable for training data; everything else is gated.
ALLOWED_LICENSES = {
    "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc", "cc0-1.0",
    "cc-by-4.0", "unlicense", "public-domain",
}


@dataclass(slots=True)
class Verdict:
    compliant: bool
    pii_types: list[str] = field(default_factory=list)
    license: str | None = None
    reasons: list[str] = field(default_factory=list)
    text: str = ""  # redacted body; goes to object storage, not the DB row

    def as_dict(self) -> dict:
        return {
            "compliant": self.compliant,
            "pii_types": self.pii_types,
            "license": self.license,
            "reasons": self.reasons,
        }


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Replace PII with <TYPE> placeholders; return (text, types found)."""
    found = []
    for name, rx in _PII_PATTERNS.items():
        text, n = rx.subn(f"<{name}>", text)
        if n:
            found.append(name)
    return text, sorted(found)


def license_allowed(license_id: str | None) -> bool:
    if license_id is None:
        return True  # unknown license handled by policy; default allow for non-code
    return license_id.strip().lower() in ALLOWED_LICENSES


def is_safe(text: str) -> bool:
    return not any(rx.search(text) for rx in _SECRET_PATTERNS)


def evaluate(text: str, metadata: dict) -> Verdict:
    redacted, pii = redact_pii(text)
    license_id = metadata.get("license")
    reasons: list[str] = []

    if not license_allowed(license_id):
        reasons.append(f"license:{license_id}")
    if not is_safe(text):
        reasons.append("unsafe:secret_material")

    return Verdict(
        compliant=not reasons, pii_types=pii, license=license_id, reasons=reasons, text=redacted
    )
