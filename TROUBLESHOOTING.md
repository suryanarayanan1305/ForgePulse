# FORGEPULSE: Forward Deployed Engineer Troubleshooting Playbook

This document details common shop-floor and cloud deployment failure scenarios, their root causes, and step-by-step resolution procedures.

---

## Scenario 1: MQTT Broker Unreachable / Network Partition

### Symptom:
`GET /api/v1/health` reports `"mqtt_broker": {"status": "DISCONNECTED"}` and dashboard shows `"MQTT Broker: DISCONNECTED"`.

### Diagnostics:
1. Check if Mosquitto container is running:
   ```bash
   docker ps -f name=forgepulse-mosquitto
   ```
2. Verify MQTT port binding:
   ```bash
   netstat -an | grep 1883
   ```
3. Inspect Mosquitto broker logs:
   ```bash
   docker logs forgepulse-mosquitto
   ```

### Fix / Recovery:
- The backend's Paho-MQTT subscriber runs in an auto-reconnect loop with exponential backoff.
- Once the broker restarts, the subscriber automatically rejoins the cluster and resumes telemetry ingestion without restarting the FastAPI process.

---

## Scenario 2: High Alert Volume / Alert Storm

### Symptom:
Anomalous condition causes thousands of repeated messages on topic `factory/plant-a/cnc-001/telemetry`.

### Diagnostics:
- Check `alerts` table in PostgreSQL for open alerts within the cooldown window:
  ```sql
  SELECT alert_type, count(*) FROM alerts WHERE machine_id = 'CNC-001' GROUP BY alert_type;
  ```

### Built-in Mitigation:
- `AlertService` checks `cooldown_expires_at > NOW()`. If an open alert of the same type already exists, duplicate alerts are discarded in memory before writing to the database.

---

## Scenario 3: Stale Telemetry Stream (Dead Sensor / Offline Gateway)

### Symptom:
Dashboard shows `Telemetry Stream: IDLE` and machine `last_seen_at` is older than 30 seconds.

### Diagnostics:
1. Verify edge simulator / gateway publisher process is running.
2. Check MQTT topic subscription permissions.
3. Query latest database record:
   ```sql
   SELECT machine_id, max(timestamp) FROM telemetry GROUP BY machine_id;
   ```
