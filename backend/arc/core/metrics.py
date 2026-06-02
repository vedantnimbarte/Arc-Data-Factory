"""Prometheus metrics. Honors CLAUDE.md: every service must expose metrics.

Stages share one registry and emit a common set of metrics labeled by
`stage`, so Grafana dashboards and queue-depth autoscaling work uniformly.
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, multiprocess

# Pipeline-wide metric vocabulary. Label by stage/service for one dashboard.
DOCS_PROCESSED = Counter(
    "arc_documents_processed_total",
    "Documents processed by a stage.",
    ["stage", "result"],  # result: ok|dropped|error
)

STAGE_DURATION = Histogram(
    "arc_stage_duration_seconds",
    "Wall-clock duration of a stage run.",
    ["stage"],
    buckets=(0.1, 0.5, 1, 5, 15, 60, 300, 900, 3600),
)

QUEUE_DEPTH = Gauge(
    "arc_queue_depth",
    "Pending tasks per stage queue (drives autoscaling).",
    ["queue"],
)

JOBS_INFLIGHT = Gauge(
    "arc_jobs_inflight",
    "Jobs currently running.",
    ["stage"],
)

BYTES_STORED = Counter(
    "arc_bytes_stored_total",
    "Bytes written to object storage.",
    ["bucket"],
)


def worker_registry() -> CollectorRegistry:
    """Registry for Celery/Ray workers (multiprocess-safe via env PROMETHEUS_MULTIPROC_DIR)."""
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return registry
