"""End-to-end pipeline test against the live dev stack.

Skipped unless ARC_RUN_INTEGRATION=1 (needs Postgres + Redis + MinIO from
`docker compose -f infra/docker-compose.yml up`). Drives every stage
synchronously through the orchestrator using the inline connector, then
asserts the dataset is READY with a manifest and shards.
"""

from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("ARC_RUN_INTEGRATION") != "1",
    reason="set ARC_RUN_INTEGRATION=1 and start the dev stack to run",
)


@pytest.mark.integration
async def test_full_pipeline_inline_source():
    from arc.core.db import session_scope
    from arc.core.storage import object_store
    from arc.db.enums import DatasetStatus, SourceType, Stage
    from arc.db.models import Dataset, Source
    from arc.db.repositories import DatasetRepository, ShardRepository, SourceRepository
    from arc.orchestrator.service import OrchestratorService
    from arc.services import bootstrap  # noqa: F401

    store = object_store()
    await store.ensure_buckets()

    docs = [{"id": f"d{i}", "text": f"Sample document number {i}. " * 40} for i in range(5)]
    docs.append(dict(docs[0]))  # near-duplicate to exercise the deduper

    async with session_scope() as session:
        ds = await DatasetRepository(session).add(
            Dataset(name="it-dataset", version=f"v{uuid.uuid4().hex[:6]}")
        )
        src = await SourceRepository(session).add(
            Source(
                name="inline", type=SourceType.WEB_DATASET, url="http://inline.local",
                config={"documents": docs},
            )
        )
        dataset_id, source_id = ds.id, src.id

    # Drive each stage to completion in canonical order.
    async with session_scope() as session:
        orch = OrchestratorService(session, store)
        run = await orch.create_run(dataset_id, None)
        run_id = run.id

    for stage in Stage.order():
        cursor: dict = {"source_id": str(source_id)} if stage is Stage.COLLECT else {}
        params = {"source_id": str(source_id)} if stage is Stage.COLLECT else {}
        done = False
        while not done:
            async with session_scope() as session:
                orch = OrchestratorService(session, store)
                # params travel via StageInput; collector reads source_id from params.
                from arc.contracts import StageInput

                inp = StageInput(
                    run_id=run_id, dataset_id=dataset_id, stage=stage,
                    cursor=cursor if stage is Stage.COLLECT else cursor, params=params,
                )
                from arc.services.base import get_stage

                result = await get_stage(stage).run(session, store, inp)
                cursor = result.cursor
                done = result.done

    async with session_scope() as session:
        ds = await DatasetRepository(session).get(dataset_id)
        shards = await ShardRepository(session).list(dataset_id)
        assert ds is not None and ds.status is DatasetStatus.READY
        assert ds.manifest_uri is not None
        assert len(shards) >= 1
