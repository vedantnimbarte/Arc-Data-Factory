"""Cross-cutting security: API auth and the collector SSRF guard.

Addresses the review's top finding (the API was wide open) and the
untrusted-URL ingestion risk in the web/RFC/docs collectors.
"""
