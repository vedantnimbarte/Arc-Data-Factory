"""Ray bootstrap — the data-parallel compute engine for heavy stages.

Used inside Celery tasks for dedupe (partitioned MinHash/LSH) and tokenize
(parallel batch encoding). Single-node local by default; set ARC_RAY_ADDRESS
to attach to a cluster (KubeRay) with no code change.
"""

from __future__ import annotations

import ray

from arc.core.config import settings
from arc.core.logging import get_logger

log = get_logger("compute")


def ensure_ray() -> None:
    """Idempotent Ray init. Safe to call at the top of any Ray-backed task."""
    if ray.is_initialized():
        return
    ray.init(
        address=settings.ray_address or None,  # empty ARC_RAY_ADDRESS => local, as documented
        num_cpus=settings.ray_num_cpus,
        ignore_reinit_error=True,
        log_to_driver=False,
        configure_logging=False,
    )
    log.info("ray_initialized", address=settings.ray_address or "local")
