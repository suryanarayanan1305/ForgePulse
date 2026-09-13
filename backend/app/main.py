"""
main.py — ForgePulse FastAPI Application Entrypoint & Lifespan Management
==========================================================================

RESPONSIBILITIES:
  1. Configures CORS middleware for React frontend integration
  2. Lifespan: Initializes database connection pool and starts resilient MQTT subscriber
  3. Registers all versioned REST API routers (/api/v1/...)
  4. Exposes OpenAPI documentation at /docs and /redoc
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_engine, close_engine, init_db_and_seed
from app.core.logging import configure_logging, get_logger
from app.mqtt.client import mqtt_subscriber
from app.mqtt.handlers import set_event_loop, on_mqtt_message_received

# Import API Routers
from app.api.v1.health import router as health_router
from app.api.v1.machines import router as machines_router
from app.api.v1.telemetry import router as telemetry_router, telemetry_ingest_router
from app.api.v1.digital_twin import router as digital_twin_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.simulation import router as simulation_router

# Configure structured JSON logging
configure_logging()
logger = get_logger("forgepulse.main")
settings = get_settings()


async def _background_simulation_loop():
    """
    Background worker that runs the machine physics and PLC scan loop.
    Enables live real-time telemetry streaming in cloud deployments (Render)
    and zero-setup local development without needing a separate simulator process.
    """
    from simulator.machine_simulator import create_fleet
    from simulator.plc_simulator import create_plc_fleet
    from app.core.database import get_db_context
    from app.schemas.telemetry import TelemetryIngest
    from app.services.telemetry_service import telemetry_service
    from simulator.main import get_orchestrator

    orch = get_orchestrator()
    if not orch._machine_fleet:
        orch._machine_fleet = create_fleet()
        orch._machine_map = {m.config.machine_id: m for m in orch._machine_fleet}
        orch._plc_map = create_plc_fleet(orch._machine_fleet)

    fleet = orch._machine_fleet
    plcs = orch._plc_map

    logger.info("Internal machine simulation background worker started.")
    while True:
        try:
            orch._fault_injector.check_expirations(orch._machine_map)
            for m in fleet:
                m.tick(dt=2.0)
                snapshot = m.get_snapshot()
                plc = plcs[m.config.machine_id]
                scan = plc.scan(snapshot)
                payload_dict = plc.build_telemetry_payload(scan, production_count=m.state.production_count)
                validated = TelemetryIngest.model_validate(payload_dict)
                async with get_db_context() as db:
                    await telemetry_service.process_and_persist_telemetry(db, validated)
        except Exception as e:
            logger.debug(f"Simulation worker error: {e}")
        await asyncio.sleep(2.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager.
    Runs startup actions before requests are served, and shutdown cleanup upon exit.
    """
    logger.info("=" * 60)
    logger.info(f"  FORGEPULSE Industrial IoT Backend v{settings.APP_VERSION}")
    logger.info(f"  Environment: {settings.APP_ENV} | Debug: {settings.DEBUG}")
    logger.info("=" * 60)

    # 1. Initialize DB Engine & Auto-Seed Schema
    create_engine()
    await init_db_and_seed()

    # 2. Hook MQTT client to async event loop
    loop = asyncio.get_running_loop()
    set_event_loop(loop)
    mqtt_subscriber.message_callback = on_mqtt_message_received
    mqtt_subscriber.start()

    # 3. Start integrated cloud simulation worker if enabled
    sim_task = None
    if settings.ENABLE_INTERNAL_SIMULATOR:
        sim_task = asyncio.create_task(_background_simulation_loop())

    logger.info("ForgePulse Backend startup sequence complete.")
    yield

    # Shutdown sequence
    logger.info("ForgePulse Backend shutting down...")
    if sim_task:
        sim_task.cancel()
    mqtt_subscriber.stop()
    await close_engine()
    logger.info("ForgePulse Backend shutdown complete.")


# Initialize FastAPI App
app = FastAPI(
    title="FORGEPULSE — Industrial IoT & Digital Twin API",
    description=(
        "Production-style backend for manufacturing telemetry ingestion, "
        "digital twins, transparent machine health scoring, and predictive maintenance."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register REST Routers
API_V1_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_V1_PREFIX)
app.include_router(machines_router, prefix=API_V1_PREFIX)
app.include_router(telemetry_router, prefix=API_V1_PREFIX)
app.include_router(telemetry_ingest_router, prefix=API_V1_PREFIX)
app.include_router(digital_twin_router, prefix=API_V1_PREFIX)
app.include_router(alerts_router, prefix=API_V1_PREFIX)
app.include_router(analytics_router, prefix=API_V1_PREFIX)
app.include_router(simulation_router, prefix=API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "FORGEPULSE Industrial IoT API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{API_V1_PREFIX}/health",
    }
