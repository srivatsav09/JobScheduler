"""
Centralized configuration using pydantic-settings.

How it works:
- Reads environment variables automatically (e.g., POSTGRES_HOST env var → Settings.POSTGRES_HOST)
- Falls back to defaults defined here if env vars are not set
- Can also read from a .env file in the project root

Every module imports `settings` from here instead of hardcoding values.
This is standard practice in production Python apps.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── PostgreSQL ──────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "jobscheduler"
    POSTGRES_PASSWORD: str = "jobscheduler"
    POSTGRES_DB: str = "jobscheduler"

    # ── Redis ───────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ── Worker ──────────────────────────────────────────────────
    WORKER_POOL_SIZE: int = 4          # number of threads in the worker pool
    WORKER_POLL_INTERVAL: float = 0.5  # seconds between scheduler loop ticks

    # ── Retry ───────────────────────────────────────────────────
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_BASE: float = 2.0    # exponential backoff base (seconds)

    # ── Scheduler ───────────────────────────────────────────────
    DEFAULT_SCHEDULING_POLICY: str = "fcfs"
    ROUND_ROBIN_TIME_QUANTUM: float = 5.0  # seconds per job in Round Robin

    # ── App ─────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    @property
    def database_url(self) -> str:
        """Async connection string for FastAPI (uses asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync connection string for worker threads (uses psycopg2 driver)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton — import this everywhere
settings = Settings()
