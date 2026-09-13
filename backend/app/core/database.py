"""
core/database.py — SQLAlchemy 2.0 Database Engine & Session Management
=======================================================================
Manages the PostgreSQL connection pool for the FastAPI application.

ARCHITECTURE:
  FastAPI ──► Session ──► SQLAlchemy Engine ──► asyncpg ──► PostgreSQL
                 │
                 └── Injected via Depends(get_async_session) in route handlers

WHY ASYNC (asyncpg)?
  FastAPI runs on an async event loop (ASGI via Uvicorn).
  Using a synchronous PostgreSQL driver (psycopg2) would BLOCK the event loop
  during every database query — killing concurrency entirely.
  asyncpg provides true async/await database calls, allowing the event loop to
  handle other requests while waiting for DB responses.

CONNECTION POOLING:
  Creating a new database connection per request is expensive (~50ms overhead).
  SQLAlchemy's connection pool maintains a warm pool of reusable connections.
  Settings (from config):
    pool_size=5     → 5 permanent connections always maintained
    max_overflow=10 → Up to 10 additional connections under peak load
    pool_timeout=30 → Raise error after 30s if no connection is available

  At our scale (5 machines × 1 reading/sec), pool_size=5 is more than enough.
  For 1000 concurrent API users, you'd increase these values.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 Declarative Base.
    All ORM models inherit from this class.
    It provides the metadata registry that SQLAlchemy uses to know
    which tables exist and how they map to Python classes.
    """
    pass


def create_engine():
    """
    Creates and configures the async SQLAlchemy engine.

    The engine is a FACTORY for database connections — it manages the
    connection pool but does not itself hold an open connection.

    Called once at application startup.
    """
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url_async,
        # Pool configuration
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,   # Test connections before use (detects stale connections)
        # Echo SQL queries to logger in debug mode
        echo=settings.DEBUG,
    )

    logger.info(
        "SQLAlchemy engine created",
        extra={
            "event": "DB_ENGINE_CREATED",
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "db": settings.POSTGRES_DB,
            "pool_size": settings.DB_POOL_SIZE,
        },
    )
    return engine


# Module-level engine and session factory — created once at startup
# WHY MODULE LEVEL?
#   FastAPI's dependency injection (Depends) calls get_async_session on every
#   request. If we created a new engine on every request, we'd have no pooling.
#   Module-level singletons ensure the pool is shared across all requests.
_engine = None
_async_session_factory = None


def get_engine():
    """Returns the module-level async engine (creates it if not yet initialized)."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Returns the module-level session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,  # Prevent "DetachedInstanceError" after commit
            autocommit=False,
            autoflush=False,
        )
    return _async_session_factory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    Usage in a route handler:
        @router.get("/machines")
        async def list_machines(db: AsyncSession = Depends(get_async_session)):
            result = await db.execute(select(Machine))
            return result.scalars().all()

    HOW IT WORKS:
      1. FastAPI calls this generator before the route handler executes.
      2. A new AsyncSession is created from the pool.
      3. The session is yielded to the route handler.
      4. After the response is sent, the `finally` block closes the session,
         returning the underlying connection back to the pool.
      5. If an error occurs, the session is still properly closed.

    The session is NOT committed here — services are responsible for
    committing transactions explicitly. This prevents partial commits
    from leaking if an error occurs mid-transaction.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager version of get_async_session.
    Used by background workers (MQTT ingestion) that don't run inside
    FastAPI's request/response cycle and therefore can't use Depends().

    Usage in MQTT handler:
        async with get_db_context() as db:
            await telemetry_service.persist(db, reading)
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> dict:
    """
    Performs a lightweight database connectivity check.
    Used by the /health endpoint to report DB status to the operations dashboard.

    Returns:
        {"status": "healthy", "latency_ms": 12.3}
        or
        {"status": "unhealthy", "error": "connection refused"}
    """
    import time
    from sqlalchemy import text

    start = time.monotonic()
    try:
        async with get_db_context() as db:
            await db.execute(text("SELECT 1"))
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as e:
        logger.error("Database health check failed", extra={"error": str(e)})
        return {"status": "unhealthy", "error": str(e)}


async def close_engine() -> None:
    """
    Gracefully disposes the engine and closes all pooled connections.
    Called during application shutdown (FastAPI lifespan).
    Failing to do this can cause connection leaks.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        logger.info("SQLAlchemy engine disposed", extra={"event": "DB_ENGINE_DISPOSED"})
        _engine = None
