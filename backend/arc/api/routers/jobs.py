"""Jobs & runs: status queries for the dashboard Jobs page."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from arc.api.deps import PrincipalDep, SessionDep
from arc.api.schemas import JobOut, RunOut
from arc.db.enums import JobStatus
from arc.db.repositories import JobRepository, RunRepository

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs", response_model=list[JobOut], summary="List jobs")
async def list_jobs(session: SessionDep, _: PrincipalDep, status_filter: JobStatus | None = None):
    return list(await JobRepository(session).list(status=status_filter))


@router.get("/jobs/{job_id}", response_model=JobOut, summary="Get a job")
async def get_job(job_id: uuid.UUID, session: SessionDep, _: PrincipalDep):
    job = await JobRepository(session).get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    return job


@router.get("/runs/{run_id}", response_model=RunOut, summary="Get a pipeline run")
async def get_run(run_id: uuid.UUID, session: SessionDep, _: PrincipalDep):
    run = await RunRepository(session).get(run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "run not found")
    return run
