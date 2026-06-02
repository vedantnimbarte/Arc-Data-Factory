"""API gateway — the control plane.

Routes call services and enqueue work; they contain NO business logic and do
NO heavy compute (CLAUDE.md: business logic isolated from API routes). Every
endpoint is typed with Pydantic and documented in OpenAPI.
"""
