"""Pipeline services. Each service is an isolated package:

    domain.py   pure logic (no I/O) — unit-tested in isolation
    service.py  the PipelineStage implementation (orchestrates I/O + domain)
    tasks.py    the Celery task wrapper
    connectors/ (collector only) source adapters

Business logic lives in domain.py and service.py — never in API routes or
Celery tasks. Composition over inheritance: services compose repositories,
the object store, and domain functions.
"""
