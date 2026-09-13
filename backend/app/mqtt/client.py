"""
mqtt/client.py — Resilient MQTT Subscriber Client for Telemetry Ingestion
===========================================================================

RESPONSIBILITIES:
  1. Subscribes to telemetry topics: factory/+/+/telemetry
  2. Subscribes to event topics: factory/+/+/events
  3. Uses QoS 1 for reliable delivery
  4. Automatically reconnects if broker goes down
  5. Dispatches messages to asynchronous background ingestion worker
"""

import asyncio
import json
import logging
import threading
from typing import Callable, Optional
import paho.mqtt.client as mqtt

from app.core.config import get_settings
from app.core.logging import get_logger, MQTTEventLogger

logger = get_logger(__name__)
mqtt_logger = MQTTEventLogger()


class MQTTSubscriberClient:
    """Resilient MQTT ingestion subscriber."""

    def __init__(self, message_callback: Optional[Callable[[str, bytes], None]] = None) -> None:
        self.settings = get_settings()
        self.message_callback = message_callback
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
        self.last_message_time: Optional[float] = None
        self.messages_received = 0

    def start(self) -> None:
        """Initializes and connects MQTT client in a background network loop."""
        self.client = mqtt.Client(
            client_id=self.settings.MQTT_CLIENT_ID,
            clean_session=False,  # Persistent session for QoS 1
            protocol=mqtt.MQTTv311,
        )

        if self.settings.MQTT_USERNAME and self.settings.MQTT_PASSWORD:
            self.client.username_pw_set(self.settings.MQTT_USERNAME, self.settings.MQTT_PASSWORD)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        logger.info(f"Connecting MQTT subscriber to {self.settings.MQTT_BROKER_HOST}:{self.settings.MQTT_BROKER_PORT}")
        try:
            self.client.connect_async(
                host=self.settings.MQTT_BROKER_HOST,
                port=self.settings.MQTT_BROKER_PORT,
                keepalive=self.settings.MQTT_KEEPALIVE,
            )
            self.client.loop_start()
        except Exception as e:
            logger.warning(f"Initial MQTT broker connection could not be established immediately: {e}. Will auto-retry.")

    def stop(self) -> None:
        """Stops network loop and disconnects cleanly."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            logger.info("MQTT subscriber stopped.")

    def _on_connect(self, client, userdata, flags, rc: int) -> None:
        if rc == 0:
            self.is_connected = True
            mqtt_logger.connected(self.settings.MQTT_BROKER_HOST, self.settings.MQTT_BROKER_PORT)

            # Wildcard subscription: factory/+/+/telemetry (covers all plants and machines)
            telemetry_topic = f"{self.settings.MQTT_TOPIC_PREFIX}/+/+/telemetry"
            event_topic = f"{self.settings.MQTT_TOPIC_PREFIX}/+/+/events"

            self.client.subscribe([(telemetry_topic, self.settings.MQTT_QOS), (event_topic, self.settings.MQTT_QOS)])
            logger.info(f"Subscribed to MQTT topics: {telemetry_topic}, {event_topic} with QoS {self.settings.MQTT_QOS}")
        else:
            logger.error(f"MQTT connection failed with return code {rc}")

    def _on_disconnect(self, client, userdata, rc: int) -> None:
        self.is_connected = False
        mqtt_logger.disconnected(rc)
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect (rc={rc}). Paho will automatically reconnect.")

    def _on_message(self, client, userdata, message) -> None:
        import time
        self.messages_received += 1
        self.last_message_time = time.time()
        topic = message.topic
        payload = message.payload

        if self.message_callback:
            try:
                self.message_callback(topic, payload)
            except Exception as e:
                logger.error(f"Error executing message callback for {topic}: {e}", exc_info=True)


mqtt_subscriber = MQTTSubscriberClient()
