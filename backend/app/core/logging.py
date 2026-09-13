"""
core/logging.py — Structured Application Logging
===================================================
Configures structured JSON logging for ForgePulse.

WHY STRUCTURED LOGGING?
  In production, logs are aggregated by systems like:
  - Render (Log Drain) → Papertrail / Datadog
  - AWS CloudWatch → Log Insights
  - ELK Stack (Elasticsearch, Logstash, Kibana)

  Plain text logs are difficult to query:
    "Find all telemetry ingestion failures for CNC-001 in the last hour"
    → Nearly impossible with grep on plain text.

  JSON logs are machine-queryable:
    { "machine_id": "CNC-001", "event": "TELEMETRY_INGESTION_ERROR", ... }
    → One Elasticsearch query, instant results.

HOW IT WORKS:
  We use `python-json-logger` to format all log records as JSON.
  In development (DEBUG=True), we also emit human-readable console output.
  Every log record automatically includes:
    - timestamp (UTC ISO8601)
    - level
    - logger name (module path)
    - message
    - any extra fields passed as kwargs
"""

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings


def configure_logging() -> None:
    """
    Sets up structured logging for the entire application.
    Called once at startup from app/main.py.
    """
    settings = get_settings()

    # Root log level
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # --- JSON Handler (always active) ---
    # Outputs every log record as a JSON line to stdout.
    # Production log aggregators (Datadog, Papertrail) parse this directly.
    json_handler = logging.StreamHandler(sys.stdout)
    json_handler.setLevel(log_level)

    # Format: timestamp, level, logger name, message, + any extra fields
    json_formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )
    json_handler.setFormatter(json_formatter)

    # --- Configure root logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(json_handler)

    # Suppress overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("paho.mqtt").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger for a specific module.

    Usage in any module:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Telemetry received", extra={"machine_id": "CNC-001", "temperature": 72.4})

    The `extra` dict adds arbitrary fields to the JSON log output.
    This is how we correlate logs by machine_id, alert_id, etc.
    """
    return logging.getLogger(name)


class MQTTEventLogger:
    """
    Specialized logger for MQTT events.
    Adds structured context to every log record automatically.

    Used by: app/mqtt/client.py, app/mqtt/handlers.py
    """

    def __init__(self) -> None:
        self._logger = get_logger("forgepulse.mqtt")

    def connected(self, broker_host: str, broker_port: int) -> None:
        self._logger.info(
            "MQTT broker connected",
            extra={"event": "MQTT_CONNECTED", "broker_host": broker_host, "broker_port": broker_port},
        )

    def disconnected(self, reason_code: int) -> None:
        self._logger.warning(
            "MQTT broker disconnected",
            extra={"event": "MQTT_DISCONNECTED", "reason_code": reason_code},
        )

    def reconnecting(self, attempt: int) -> None:
        self._logger.info(
            "MQTT reconnecting",
            extra={"event": "MQTT_RECONNECTING", "attempt": attempt},
        )

    def message_received(self, topic: str, machine_id: str) -> None:
        self._logger.debug(
            "MQTT message received",
            extra={"event": "MQTT_MSG_RECEIVED", "topic": topic, "machine_id": machine_id},
        )

    def message_validation_error(self, topic: str, error: str, raw_payload: str) -> None:
        self._logger.error(
            "MQTT message validation failed",
            extra={
                "event": "MQTT_VALIDATION_ERROR",
                "topic": topic,
                "error": error,
                # Never log full payload in production if it contains PII
                "payload_preview": raw_payload[:200],
            },
        )


class TelemetryEventLogger:
    """
    Specialized logger for telemetry ingestion pipeline events.
    Used by: app/mqtt/handlers.py, app/services/telemetry_service.py
    """

    def __init__(self) -> None:
        self._logger = get_logger("forgepulse.telemetry")

    def persisted(self, machine_id: str, timestamp: str, is_anomaly: bool) -> None:
        self._logger.info(
            "Telemetry persisted",
            extra={
                "event": "TELEMETRY_PERSISTED",
                "machine_id": machine_id,
                "timestamp": timestamp,
                "is_anomaly": is_anomaly,
            },
        )

    def anomaly_detected(self, machine_id: str, method: str, metric: str, value: float) -> None:
        self._logger.warning(
            "Anomaly detected in telemetry",
            extra={
                "event": "ANOMALY_DETECTED",
                "machine_id": machine_id,
                "detection_method": method,
                "metric": metric,
                "observed_value": value,
            },
        )

    def db_error(self, machine_id: str, error: str) -> None:
        self._logger.error(
            "Database error during telemetry persistence",
            extra={"event": "TELEMETRY_DB_ERROR", "machine_id": machine_id, "error": error},
        )


class AlertEventLogger:
    """
    Specialized logger for the alert engine.
    Used by: app/services/alert_service.py
    """

    def __init__(self) -> None:
        self._logger = get_logger("forgepulse.alerts")

    def alert_created(self, machine_id: str, alert_type: str, severity: str, value: float) -> None:
        self._logger.warning(
            "Alert created",
            extra={
                "event": "ALERT_CREATED",
                "machine_id": machine_id,
                "alert_type": alert_type,
                "severity": severity,
                "observed_value": value,
            },
        )

    def alert_suppressed(self, machine_id: str, alert_type: str, cooldown_remaining: float) -> None:
        self._logger.debug(
            "Alert suppressed (cooldown active)",
            extra={
                "event": "ALERT_SUPPRESSED",
                "machine_id": machine_id,
                "alert_type": alert_type,
                "cooldown_remaining_seconds": cooldown_remaining,
            },
        )
