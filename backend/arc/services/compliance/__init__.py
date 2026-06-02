"""Compliance service: PII, license, and safety gating for training data.

This stage did not exist in the original docs; the architecture review flagged
its absence as a legal/security must-have. Documents failing any gate are
REJECTED and never reach a shard.
"""
