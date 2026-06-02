"""Unit tests for compliance gating (regex fallback path)."""

from __future__ import annotations

from arc.services.compliance import domain


def test_detect_pii_email_and_ssn():
    pii = domain.detect_pii("contact me at a@b.com, ssn 123-45-6789")
    assert "EMAIL_ADDRESS" in pii or "US_SSN" in pii  # presidio or fallback


def test_license_allowlist():
    assert domain.license_allowed("MIT")
    assert domain.license_allowed("apache-2.0")
    assert not domain.license_allowed("GPL-3.0")
    assert domain.license_allowed(None)  # unknown -> allowed by default policy


def test_unsafe_secret_material_blocked():
    assert not domain.is_safe("-----BEGIN PRIVATE KEY-----\nabc")
    assert domain.is_safe("regular text")


def test_evaluate_rejects_disallowed_license():
    v = domain.evaluate("clean text", {"license": "GPL-3.0"}, block_pii=False)
    assert not v.compliant
    assert any(r.startswith("license:") for r in v.reasons)


def test_evaluate_compliant_clean_doc():
    v = domain.evaluate("just some safe prose", {"license": "mit"}, block_pii=True)
    assert v.compliant
    assert v.as_dict()["compliant"] is True
