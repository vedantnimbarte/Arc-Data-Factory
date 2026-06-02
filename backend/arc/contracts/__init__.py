"""Shared data contracts that cross service boundaries.

Every stage consumes a StageInput and returns a StageResult. Hand-offs move
by object-storage URI + DB metadata, never by passing payloads in memory —
so services stay decoupled and the contract is the only coupling point.
"""

from arc.contracts.pipeline import StageInput, StageResult

__all__ = ["StageInput", "StageResult"]
