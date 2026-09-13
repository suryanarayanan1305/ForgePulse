"""
api/v1/health.py — System Health & Diagnostics Endpoints
=========================================================
"""

import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import check_database_health, get_async_session
from app.mqtt.client import mqtt_subscriber

router = APIRouter(tags=["Diagnostics & Health"])


@router.get("/health", summary="System Health & Diagnostics")
async def get_system_health():
    """
    Returns full connectivity and operational diagnostics across:
    - FastAPI Application
    - PostgreSQL Database
    - MQTT Broker
    - Telemetry Ingestion Activity
    """
    db_health = await check_database_health()
    now_ts = time.time()
    last_msg_seconds_ago = None
    if mqtt_subscriber.last_message_time:
        last_msg_seconds_ago = round(now_ts - mqtt_subscriber.last_message_time, 1)

    mqtt_status = "CONNECTED" if mqtt_subscriber.is_connected else "DISCONNECTED"
    telemetry_status = "RECEIVING" if (last_msg_seconds_ago is not None and last_msg_seconds_ago < 10) else "IDLE"

    overall_status = "HEALTHY" if (db_health.get("status") == "healthy" and mqtt_subscriber.is_connected) else "DEGRADED"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "api": {"status": "HEALTHY", "version": "1.0.0"},
            "database": {
                "status": "CONNECTED" if db_health.get("status") == "healthy" else "DISCONNECTED",
                "latency_ms": db_health.get("latency_ms"),
                "error": db_health.get("error"),
            },
            "mqtt_broker": {
                "status": mqtt_status,
                "messages_received": mqtt_subscriber.messages_received,
                "last_message_seconds_ago": last_msg_seconds_ago,
            },
            "telemetry_stream": {
                "status": telemetry_status,
                "freshness_seconds": last_msg_seconds_ago,
            },
            "analytics_engine": {"status": "READY"},
        },
    }
