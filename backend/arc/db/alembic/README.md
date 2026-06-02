# Migrations

```bash
# from backend/
alembic upgrade head            # apply
alembic revision --autogenerate -m "msg"   # diff models -> new migration
alembic downgrade -1            # roll back one
```

`env.py` injects the DB URL from `arc.core.config` (sync psycopg URL), so no
credentials live in `alembic.ini`. The baseline (`0001`) creates the full
schema from the ORM metadata.
