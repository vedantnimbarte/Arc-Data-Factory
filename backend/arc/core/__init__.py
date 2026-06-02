"""Shared infrastructure: settings, database, storage, logging, metrics.

This package holds zero business logic. Every service depends on `core`;
`core` depends on no service. This keeps service boundaries clean.
"""
