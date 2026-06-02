"""Typed application settings, loaded from the environment.

Single source of truth for configuration. Services never read os.environ
directly — they import `settings`. This makes every knob discoverable and
testable, and keeps secrets out of code.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ARC_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # --- General ---
    environment: Literal["dev", "staging", "prod"] = "dev"
    service_name: str = "arc"
    log_level: str = "INFO"
    log_json: bool = True

    # --- Database (PostgreSQL, async) ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "arc"
    postgres_password: str = "arc"
    postgres_db: str = "arc"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # --- Redis: separate cache vs broker (avoids the single-Redis bottleneck) ---
    redis_cache_url: RedisDsn = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- Object storage (S3-compatible: MinIO in dev, R2/S3 in prod by config) ---
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_raw: str = "arc-raw"
    s3_bucket_datasets: str = "arc-datasets"
    s3_use_tls: bool = False

    # --- Ray ---
    ray_address: str | None = None  # None => local single-node; set for cluster
    ray_num_cpus: int | None = None

    # --- Pipeline tuning ---
    raw_bundle_target_mb: int = 128  # pack raw docs into bundles, avoid small-file storms
    shard_target_rows: int = 100_000
    minhash_num_perm: int = 128
    lsh_threshold: float = 0.85

    # --- Security ---
    api_keys: list[str] = Field(default_factory=list)
    allow_collector_private_ranges: bool = False  # SSRF guard default-deny

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def alembic_database_url(self) -> str:
        # Alembic runs sync; use psycopg-style sync URL.
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
