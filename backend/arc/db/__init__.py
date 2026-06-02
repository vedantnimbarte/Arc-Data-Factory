"""Persistence layer: ORM models, enums, and repositories.

Repositories are the ONLY place that issues queries. Services depend on
repositories, never on the session directly — this keeps DB access testable
and isolated (CLAUDE.md: service boundaries, logic isolated from I/O).
"""
