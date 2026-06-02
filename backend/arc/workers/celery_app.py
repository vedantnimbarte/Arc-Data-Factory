"""Celery application — owns stage lifecycle and IO-bound orchestration.

Boundary rule: Celery schedules and supervises stage *tasks*; heavy
CPU/data-parallel work *inside* a task is delegated to Ray. Each stage gets
its own queue so workers scale independently and queue depth (exported to
Prometheus) can drive autoscaling.
"""

from __future__ import annotations

from celery import Celery
from kombu import Queue

from arc.core.config import settings

STAGE_QUEUES = (
    "collect",
    "clean",
    "dedupe",
    "compliance",
    "classify",
    "score",
    "tokenize",
    "shard",
    "register",
    "orchestrate",
)

celery_app = Celery(
    "arc",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[f"arc.services.{s}.tasks" for s in (
        "collector", "cleaner", "deduper", "compliance", "classifier",
        "scorer", "tokenizer", "sharder", "registry",
    )] + ["arc.orchestrator.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,            # redeliver on worker crash -> resumability
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,   # fair dispatch for long tasks
    task_track_started=True,
    result_extended=True,
    task_default_queue="orchestrate",
    task_queues=tuple(Queue(q) for q in STAGE_QUEUES),
    task_acks_on_failure_or_timeout=False,
    broker_transport_options={"visibility_timeout": 3600},
    task_routes={
        "arc.services.collector.tasks.*": {"queue": "collect"},
        "arc.services.cleaner.tasks.*": {"queue": "clean"},
        "arc.services.deduper.tasks.*": {"queue": "dedupe"},
        "arc.services.compliance.tasks.*": {"queue": "compliance"},
        "arc.services.classifier.tasks.*": {"queue": "classify"},
        "arc.services.scorer.tasks.*": {"queue": "score"},
        "arc.services.tokenizer.tasks.*": {"queue": "tokenize"},
        "arc.services.sharder.tasks.*": {"queue": "shard"},
        "arc.services.registry.tasks.*": {"queue": "register"},
        "arc.orchestrator.tasks.*": {"queue": "orchestrate"},
    },
)
