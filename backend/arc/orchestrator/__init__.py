"""Orchestrator — the workflow engine the docs lacked.

Drives a PipelineRun stage-by-stage, one batch per Celery task. After each
batch it persists a StageCheckpoint (cursor + counts); a crashed or
redelivered task resumes from that checkpoint. When a stage reports done it
advances to the next requested stage; the last stage finalizes the run.
"""
