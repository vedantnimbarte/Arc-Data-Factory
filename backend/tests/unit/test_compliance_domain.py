"""Unit tests for compliance gating: PII redaction, secrets, licenses."""

from __future__ import annotations

from arc.services.compliance import domain


def test_redact_pii_replaces_email_and_ssn():
    text, found = domain.redact_pii("contact me at a@b.com, ssn 123-45-6789")
    assert "a@b.com" not in text and "123-45-6789" not in text
    assert "<EMAIL_ADDRESS>" in text and "<US_SSN>" in text
    assert found == ["EMAIL_ADDRESS", "US_SSN"]


def test_redact_pii_phone_needs_separators():
    text, found = domain.redact_pii("call 555-123-4567 today")
    assert "555-123-4567" not in text and found == ["PHONE_NUMBER"]
    # Bare numeric constants in code are not phone numbers.
    assert domain.redact_pii("MAX = 5551234567") == ("MAX = 5551234567", [])


def test_redact_pii_keeps_git_ssh_urls():
    url = "git clone git@github.com:owner/repo.git"
    assert domain.redact_pii(url) == (url, [])


def test_license_allowlist():
    assert domain.license_allowed("MIT")
    assert domain.license_allowed("apache-2.0")
    assert not domain.license_allowed("GPL-3.0")
    assert not domain.license_allowed("none")  # repo with no license
    assert domain.license_allowed(None)  # unknown -> allowed by default policy


def test_unsafe_secret_material_blocked():
    assert not domain.is_safe("-----BEGIN RSA PRIVATE KEY-----\nabc")
    assert not domain.is_safe("aws_key = 'AKIAABCDEFGHIJKLMNOP'")
    assert not domain.is_safe("token: ghp_" + "a" * 36)
    assert domain.is_safe("regular text")


def test_evaluate_rejects_disallowed_license():
    v = domain.evaluate("clean text", {"license": "GPL-3.0"})
    assert not v.compliant
    assert any(r.startswith("license:") for r in v.reasons)


def test_evaluate_redacts_pii_instead_of_rejecting():
    v = domain.evaluate("maintainer: jane@example.org", {"license": "mit"})
    assert v.compliant
    assert v.pii_types == ["EMAIL_ADDRESS"]
    assert "jane@example.org" not in v.text
    assert "text" not in v.as_dict()  # redacted body is not stored in the DB row


def test_evaluate_rejects_secrets():
    v = domain.evaluate("key = 'AKIAABCDEFGHIJKLMNOP'", {})
    assert not v.compliant and "unsafe:secret_material" in v.reasons


def test_evaluate_compliant_clean_doc():
    v = domain.evaluate("just some safe prose", {"license": "mit"})
    assert v.compliant
    assert v.text == "just some safe prose"
    assert v.as_dict()["compliant"] is True
