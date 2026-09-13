"""
simulator/mqtt_publisher.py — Edge Gateway MQTT Publisher
==========================================================

ROLE IN THE ARCHITECTURE:
  This module represents the "IoT / Edge Gateway" layer.
  In a real IIoT system, this would be hardware like:
    - Siemens IoT2050 gateway
    - Moxa UC-Series edge computer
    - AWS Greengrass on an industrial PC

  The edge gateway's job:
    1. Read PLC tag data (via OPC-UA, Modbus, or MQTT locally)
    2. Package it as a cloud-ready payload (JSON)
    3. Publish to the cloud MQTT broker
    4. Handle network outages gracefully (buffer and retry)

  Our software edge gateway:
    1. Receives PLCScanResult from SoftwarePLC.scan()
    2. Formats it as JSON telemetry payload
    3. Publishes to Mosquitto broker via paho-mqtt
    4. Implements reconnection on broker unavailability

MQTT QoS CHOICE:
  We use QoS 1 (At Least Once delivery).

  QoS 0 (Fire and Forget): Message is sent once. If broker is unavailable,
    the message is lost permanently. Unacceptable for anomaly detection
    because a missed reading could be the one that triggered a critical alert.

  QoS 1 (At Least Once): Message is acknowledged by broker. If no ACK received,
    client retransmits. Possible duplicates — acceptable because our telemetry
    persistence is idempotent (a duplicate reading just creates a duplicate row
    with a slightly different UUID).

  QoS 2 (Exactly Once): Four-way handshake. No duplicates, guaranteed delivery.
    Overhead is excessive for high-frequency telemetry (2Hz × 5 machines = 10/sec).
    QoS 2 is appropriate for irreversible control commands (not monitoring data).

TOPIC STRUCTURE:
  factory/{plant_id}/{machine_id}/telemetry  — periodic sensor readings
  factory/{plant_id}/{machine_id}/events     — status changes, fault injections
  factory/{plant_id}/{machine_id}/status     — current machine status (retained)

  WHY HIERARCHICAL TOPICS?
    - Subscribers can use wildcards: factory/PLANT-A/+/telemetry = all machines
    - Separation of concerns: telemetry consumers don't receive event noise
    - The backend subscribes to: factory/+/+/telemetry (all plants, all machines)
"""

import json
import logging
import time
import threading
from typing import Callable, Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """
    Resilient MQTT publisher for the simulator edge gateway.

    Features:
      - Automatic reconnection on broker disconnect
      - Configurable QoS level
      - Retained messages for status topics
      - Message queuing during disconnection (paho handles internally at QoS 1)
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        client_id: str = "forgepulse-simulator",
        topic_prefix: str = "factory",
        qos: int = 1,
        username: Optional[str] = None,
        password: Optional[str] = None,
        on_connect_callback: Optional[Callable] = None,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_prefix = topic_prefix
        self.qos = qos
        self._connected = False
        self._reconnect_count = 0
        self._on_connect_callback = on_connect_callback

        # Create MQTT client
        # clean_session=True: Don't restore subscriptions on reconnect (publisher doesn't subscribe)
        self._client = mqtt.Client(
            client_id=client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311,
        )

        # Set credentials if provided (cloud MQTT brokers require authentication)
        if username and password:
            self._client.username_pw_set(username, password)

        # Register callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish

        # Statistics
        self._published_count = 0
        self._failed_count = 0

    def connect(self, max_retries: int = 10, retry_delay: float = 3.0) -> bool:
        """
        Connects to the MQTT broker with retry logic.

        In Docker Compose, the broker container may take a few seconds to start.
        We retry with backoff so the simulator doesn't crash on first startup.

        Args:
            max_retries: Maximum connection attempts (0 = infinite)
            retry_delay: Seconds between retry attempts

        Returns:
            True if connected successfully
        """
        attempt = 0
        while max_retries == 0 or attempt < max_retries:
            try:
                attempt += 1
                logger.info(
                    f"Connecting to MQTT broker {self.broker_host}:{self.broker_port} "
                    f"(attempt {attempt})"
                )
                self._client.connect(
                    host=self.broker_host,
                    port=self.broker_port,
                    keepalive=60,   # Broker sends PINGREQ if no message for 60s
                )
                # Start the network loop in a background thread
                # loop_start() is non-blocking — it creates an internal thread
                self._client.loop_start()

                # Wait up to 5s for connection to establish
                for _ in range(50):
                    if self._connected:
                        logger.info(
                            f"MQTT connected to {self.broker_host}:{self.broker_port}"
                        )
                        return True
                    time.sleep(0.1)

                logger.warning(f"MQTT connection attempt {attempt} timed out")

            except (ConnectionRefusedError, OSError) as e:
                logger.warning(
                    f"MQTT connection attempt {attempt} failed: {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)

        logger.error(f"Failed to connect to MQTT broker after {attempt} attempts")
        return False

    def disconnect(self) -> None:
        """Gracefully disconnect from the MQTT broker."""
        self._client.loop_stop()
        self._client.disconnect()
        self._connected = False
        logger.info("MQTT publisher disconnected")

    def publish_telemetry(self, plant_id: str, machine_id: str, payload: dict) -> bool:
        """
        Publishes a telemetry payload to the machine's telemetry topic.

        Topic: factory/{plant_id}/{machine_id}/telemetry
        QoS: 1 (at least once — acknowledged by broker)

        Args:
            plant_id: Plant identifier (e.g., "PLANT-A")
            machine_id: Machine identifier (e.g., "CNC-001")
            payload: Telemetry data dict (JSON-serializable)

        Returns:
            True if message was queued for delivery
        """
        topic = f"{self.topic_prefix}/{plant_id.lower()}/{machine_id.lower()}/telemetry"
        return self._publish(topic, payload, retain=False)

    def publish_status(self, plant_id: str, machine_id: str, status: str) -> bool:
        """
        Publishes the current machine status to the status topic.

        retain=True: The broker stores the last status message.
        New subscribers immediately receive the current status without
        waiting for the next periodic publish.

        INTERVIEW CONTEXT:
          "I use retained messages on the status topic so that when the
           dashboard first loads, it immediately shows the current machine
           states rather than displaying 'Unknown' until the next
           2-second telemetry publish cycle."

        Topic: factory/{plant_id}/{machine_id}/status
        """
        topic = f"{self.topic_prefix}/{plant_id.lower()}/{machine_id.lower()}/status"
        payload = {
            "machine_id": machine_id,
            "status": status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return self._publish(topic, payload, retain=True)

    def publish_event(self, plant_id: str, machine_id: str, event: dict) -> bool:
        """
        Publishes a machine event (state change, fault injection, etc.).

        Topic: factory/{plant_id}/{machine_id}/events
        """
        topic = f"{self.topic_prefix}/{plant_id.lower()}/{machine_id.lower()}/events"
        return self._publish(topic, event, retain=False)

    def _publish(self, topic: str, payload: dict, retain: bool = False) -> bool:
        """
        Internal publish method with error handling.

        If disconnected, paho-mqtt will queue the message internally
        and deliver it when reconnected (for QoS 1).
        """
        if not self._connected:
            logger.warning(f"MQTT not connected — message to {topic} may be queued")

        try:
            payload_json = json.dumps(payload, default=str)
            result = self._client.publish(
                topic=topic,
                payload=payload_json,
                qos=self.qos,
                retain=retain,
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self._published_count += 1
                logger.debug(f"Published to {topic} (total: {self._published_count})")
                return True
            else:
                self._failed_count += 1
                logger.error(f"Publish failed to {topic}: rc={result.rc}")
                return False

        except Exception as e:
            self._failed_count += 1
            logger.error(f"Publish exception to {topic}: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc: int) -> None:
        """Called by paho when connection is established."""
        if rc == 0:
            self._connected = True
            self._reconnect_count = 0
            logger.info(f"MQTT broker connected (flags={flags})")
            if self._on_connect_callback:
                self._on_connect_callback()
        else:
            # rc codes: 1=bad protocol, 2=bad client ID, 3=server unavailable,
            #           4=bad credentials, 5=not authorized
            logger.error(f"MQTT connection refused: rc={rc}")

    def _on_disconnect(self, client, userdata, rc: int) -> None:
        """
        Called by paho when disconnected.
        paho's automatic reconnect is NOT enabled by default for the publisher —
        we rely on loop_start()'s internal reconnect logic.
        """
        self._connected = False
        self._reconnect_count += 1

        if rc == 0:
            logger.info("MQTT cleanly disconnected")
        else:
            # Unexpected disconnect — paho will attempt automatic reconnection
            logger.warning(
                f"MQTT unexpected disconnect (rc={rc}, reconnect #{self._reconnect_count})"
            )

    def _on_publish(self, client, userdata, mid: int) -> None:
        """Called when a QoS 1/2 message is acknowledged by the broker."""
        logger.debug(f"MQTT message {mid} acknowledged by broker")

    @property
    def stats(self) -> dict:
        return {
            "connected": self._connected,
            "published": self._published_count,
            "failed": self._failed_count,
            "reconnects": self._reconnect_count,
        }
