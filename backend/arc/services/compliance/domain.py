"""Pure compliance logic: PII detection, license allow-list, safety check.

Presidio is used when available; a regex fallback keeps the stage functional
(and unit-testable) without the heavy model dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s-]?)\d{3}[\s-]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Permissive licenses acceptable for training data; everything else is gated.
ALLOWED_LICENSES = {
    "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc", "cc0-1.0",
    "cc-by-4.0", "unlicense", "public-domain",
}

_UNSAFE_MARKERS = ("-----begin private key-----", "-----begin rsa private key-----")


@dataclass(slots=True)
class Verdict:
    compliant: bool
    pii_types: list[str] = field(default_factory=list)
    license: str | None = None
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "compliant": self.compliant,
            "pii_types": self.pii_types,
            "license": self.license,
            "reasons": self.reasons,
        }


def detect_pii(text: str) -> list[str]:
    try:
        from presidio_analyzer import AnalyzerEngine

        engine = AnalyzerEngine()
        results = engine.analyze(text=text[:10000], language="en")
        return sorted({r.entity_type for r in results})
    except Exception:  # noqa: BLE001  fallback to regex
        found = []
        if _EMAIL_RE.search(text):
            found.append("EMAIL_ADDRESS")
        if _PHONE_RE.search(text):
            found.append("PHONE_NUMBER")
        if _SSN_RE.search(text):
            found.append("US_SSN")
        return found


def license_allowed(license_id: str | None) -> bool:
    if license_id is None:
        return True  # unknown license handled by policy; default allow for non-code
    return license_id.strip().lower() in ALLOWED_LICENSES


def is_safe(text: str) -> bool:
    low = text.lower()
    return not any(marker in low for marker in _UNSAFE_MARKERS)


def evaluate(text: str, metadata: dict, *, block_pii: bool = True) -> Verdict:
    pii = detect_pii(text)
    license_id = metadata.get("license")
    reasons: list[str] = []

    if block_pii and pii:
        reasons.append(f"pii:{','.join(pii)}")
    if not license_allowed(license_id):
        reasons.append(f"license:{license_id}")
    if not is_safe(text):
        reasons.append("unsafe:secret_material")

    return Verdict(
        compliant=not reasons, pii_types=pii, license=license_id, reasons=reasons
    )
