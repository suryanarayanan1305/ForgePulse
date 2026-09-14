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
    Supports both PostgreSQL (asyncpg) with connection pooling and SQLite (aiosqlite)
    for zero-dependency standalone local development.
    """
    settings = get_settings()

    if "sqlite" in settings.database_url_async:
        from sqlalchemy.pool import StaticPool
        engine = create_async_engine(
            settings.database_url_async,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.DEBUG,
        )
    else:
        engine = create_async_engine(
            settings.database_url_async,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )

    logger.info(
        "SQLAlchemy engine created",
        extra={
            "event": "DB_ENGINE_CREATED",
            "db_url": settings.database_url_async.split("@")[-1] if "@" in settings.database_url_async else settings.database_url_async,
        },
    )
    return engine


async def init_db_and_seed() -> None:
    """
    Initializes all database tables and seeds default manufacturing plant,
    machines, and sensors if the database is currently uninitialized.
    """
    import datetime
    from decimal import Decimal
    from sqlalchemy import select
    from app.models.plant import Plant
    from app.models.machine import Machine
    from app.models.sensor import MachineSensor

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_db_context() as db:
        stmt = select(Plant).where(Plant.plant_id == "PLANT-A")
        existing_plant = (await db.execute(stmt)).scalar_one_or_none()
        if not existing_plant:
            logger.info("Seeding initial plant, machines, and sensor configuration...")
            plant = Plant(
                plant_id="PLANT-A",
                plant_name="Chennai Advanced Manufacturing Facility",
                location="SIPCOT Industrial Complex, Irungattukottai",
                city="Chennai",
                country="India",
                timezone="Asia/Kolkata",
                is_active=True,
            )
            db.add(plant)
            await db.flush()

            machines_data = [
                Machine(
                    machine_id="CNC-001",
                    machine_name="CNC Machining Center Alpha",
                    machine_type="CNC",
                    plant_id="PLANT-A",
                    location="Bay-1, Zone-A",
                    manufacturer="Haas Automation (Simulated)",
                    model="VF-2SS",
                    serial_number="SIM-CNC-001-2022",
                    rated_rpm=Decimal("8000.0"),
                    temperature_limit=Decimal("85.0"),
                    vibration_limit=Decimal("7.5"),
                    pressure_limit=Decimal("10.0"),
                    power_limit=Decimal("22.0"),
                    current_status="STOPPED",
                    is_active=True,
                ),
                Machine(
                    machine_id="CNC-002",
                    machine_name="CNC Machining Center Beta",
                    machine_type="CNC",
                    plant_id="PLANT-A",
                    location="Bay-1, Zone-B",
                    manufacturer="Haas Automation (Simulated)",
                    model="VF-4",
                    serial_number="SIM-CNC-002-2021",
                    rated_rpm=Decimal("6000.0"),
                    temperature_limit=Decimal("82.0"),
                    vibration_limit=Decimal("7.0"),
                    pressure_limit=Decimal("10.0"),
                    power_limit=Decimal("30.0"),
                    current_status="STOPPED",
                    is_active=True,
                ),
                Machine(
                    machine_id="CNC-003",
                    machine_name="CNC Machining Center Gamma",
                    machine_type="CNC",
                    plant_id="PLANT-A",
                    location="Bay-2, Zone-A",
                    manufacturer="DMG Mori (Simulated)",
                    model="DMU 50",
                    serial_number="SIM-CNC-003-2020",
                    rated_rpm=Decimal("6000.0"),
                    temperature_limit=Decimal("80.0"),
                    vibration_limit=Decimal("7.0"),
                    pressure_limit=Decimal("9.5"),
                    power_limit=Decimal("25.0"),
                    current_status="STOPPED",
                    is_active=True,
                ),
                Machine(
                    machine_id="PRESS-001",
                    machine_name="Hydraulic Press Station 1",
                    machine_type="PRESS",
                    plant_id="PLANT-A",
                    location="Bay-3, Zone-A",
                    manufacturer="Schuler AG (Simulated)",
                    model="MSP-500",
                    serial_number="SIM-PRESS-001-2019",
                    rated_rpm=Decimal("300.0"),
                    temperature_limit=Decimal("70.0"),
                    vibration_limit=Decimal("5.0"),
                    pressure_limit=Decimal("250.0"),
                    power_limit=Decimal("75.0"),
                    current_status="STOPPED",
                    is_active=True,
                ),
                Machine(
                    machine_id="MILL-001",
                    machine_name="Vertical Milling Machine 1",
                    machine_type="MILL",
                    plant_id="PLANT-A",
                    location="Bay-2, Zone-B",
                    manufacturer="Bridgeport (Simulated)",
                    model="Series I",
                    serial_number="SIM-MILL-001-2023",
                    rated_rpm=Decimal("4000.0"),
                    temperature_limit=Decimal("75.0"),
                    vibration_limit=Decimal("6.5"),
                    pressure_limit=Decimal("8.0"),
                    power_limit=Decimal("15.0"),
                    current_status="STOPPED",
                    is_active=True,
                ),
            ]
            db.add_all(machines_data)
            await db.flush()

            # Seed 20 historical telemetry readings per machine so charts render immediately
            import random
            from app.models.telemetry import Telemetry
            base_time = datetime.datetime.now(datetime.timezone.utc)
            initial_telemetry = []
            for m in machines_data:
                for i in range(25, 0, -1):
                    t_time = base_time - datetime.timedelta(seconds=i * 2)
                    temp_base = 32.0 if m.machine_id in ("CNC-001", "CNC-002", "MILL-001") else 28.0
                    vib_base = 0.65 if m.machine_id in ("CNC-001", "CNC-002", "MILL-001") else 0.45
                    initial_telemetry.append(
                        Telemetry(
                            machine_id=m.machine_id,
                            plant_id="PLANT-A",
                            timestamp=t_time,
                            temperature=Decimal(str(round(temp_base + random.uniform(-0.5, 0.5), 2))),
                            pressure=Decimal("5.2"),
                            vibration=Decimal(str(round(vib_base + random.uniform(-0.05, 0.05), 3))),
                            rpm=Decimal("3200.0") if m.machine_id in ("CNC-001", "CNC-002", "MILL-001") else Decimal("0.0"),
                            power_consumption=Decimal("8.5") if m.machine_id in ("CNC-001", "CNC-002", "MILL-001") else Decimal("0.0"),
                            production_count=100 - i,
                            machine_status="RUNNING" if m.machine_id in ("CNC-001", "CNC-002", "MILL-001") else "STOPPED",
                            is_anomaly=False,
                        )
                    )
            db.add_all(initial_telemetry)
            await db.flush()
            logger.info("Database initialized and seeded successfully with baseline telemetry.")


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
