"""
mqtt/handlers.py — MQTT Ingestion Message Router & Async Dispatcher
====================================================================

Bridges the synchronous Paho-MQTT client thread with FastAPI's async event loop.
Uses an asyncio Queue / task runner with `get_db_context()` to safely persist
telemetry and events to PostgreSQL without blocking the MQTT network thread.
"""

import asyncio
import json
import logging
from typing import Any, Dict
from pydantic import ValidationError

from app.core.database import get_db_context
from app.core.logging import get_logger, MQTTEventLogger, TelemetryEventLogger
from app.schemas.telemetry import TelemetryIngest
from app.services.telemetry_service import telemetry_service
from app.models.event import MachineEvent

logger = get_logger(__name__)
mqtt_logger = MQTTEventLogger()
telemetry_logger = TelemetryEventLogger()

# Asyncio event loop reference
_main_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def on_mqtt_message_received(topic: str, payload_bytes: bytes) -> None:
    """
    Synchronous callback executed inside Paho-MQTT's background thread.
    Dispatches processing to FastAPI's async event loop.
    """
    if _main_loop is None or _main_loop.is_closed():
        return

    try:
        raw_text = payload_bytes.decode("utf-8")
        data = json.loads(raw_text)
    except Exception as e:
        mqtt_logger.message_validation_error(topic, f"Invalid JSON: {e}", payload_bytes.decode("utf-8", "ignore"))
        return

    # Schedule async processing in the main event loop
    asyncio.run_coroutine_threadsafe(_process_message_async(topic, data, raw_text), _main_loop)


async def _process_message_async(topic: str, data: Dict[str, Any], raw_text: str) -> None:
    """Async worker handling validation, analytical pipeline, and database persistence."""
    try:
        if topic.endswith("/telemetry"):
            await _handle_telemetry(topic, data, raw_text)
        elif topic.endswith("/events"):
            await _handle_event(topic, data)
    except Exception as e:
        logger.error(f"Error handling message on {topic}: {e}", exc_info=True)


async def _handle_telemetry(topic: str, data: Dict[str, Any], raw_text: str) -> None:
    try:
        validated = TelemetryIngest.model_validate(data)
    except ValidationError as ve:
        mqtt_logger.message_validation_error(topic, str(ve), raw_text)
        return

    # Persist in DB using async context manager
    try:
        async with get_db_context() as db:
            saved = await telemetry_service.process_and_persist_telemetry(db, validated)
            telemetry_logger.persisted(saved.machine_id, saved.timestamp.isoformat(), saved.is_anomaly)
    except Exception as dbe:
        telemetry_logger.db_error(validated.machine_id, str(dbe))


async def _handle_event(topic: str, data: Dict[str, Any]) -> None:
    machine_id = data.get("machine_id", "UNKNOWN")
    event_type = data.get("event_type", "GENERIC_EVENT")
    severity = data.get("severity", "INFO")
    message = data.get("message") or f"Event {event_type} on {machine_id}"

    try:
        async with get_db_context() as db:
            event = MachineEvent(
                machine_id=machine_id,
                event_type=event_type,
                severity=severity,
                message=message,
                event_metadata=data,
            )
            db.add(event)
            await db.commit()
            logger.info(f"Machine event recorded: {event_type} on {machine_id}")
    except Exception as e:
        logger.error(f"Failed to record event for {machine_id}: {e}")
