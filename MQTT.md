# FORGEPULSE: MQTT Architecture & Messaging Guide

## 1. Topic Hierarchy Design

ForgePulse adopts standard industrial pub/sub topic namespace conventions:

```
factory/
  └── {plant_id}/
        └── {machine_id}/
              ├── telemetry  (High-frequency periodic metrics: Temp, Vib, RPM, Power)
              ├── events     (Discrete events: Fault Injected, E-Stop, Maintenance)
              ├── alerts     (Downstream alerts raised for edge nodes)
              └── status     (Current operational state — RETAINED message)
```

### Topic Examples:
- `factory/plant-a/cnc-001/telemetry`
- `factory/plant-a/cnc-001/status` (Retained)
- `factory/plant-a/cnc-001/events`

---

## 2. QoS Level Strategy

| QoS Level | Guarantee | Overhead | Used In ForgePulse | Justification |
|---|---|---|---|---|
| **QoS 0** | At most once (Fire & Forget) | Minimum | No | Network drops cause silent telemetry loss, blinding anomaly detectors. |
| **QoS 1** | At least once (Acknowledged delivery) | Moderate | **YES (All Telemetry & Events)** | Guaranteed delivery. Duplicates are safely handled via idempotent DB storage. |
| **QoS 2** | Exactly once (4-step handshake) | High | No | Excessive roundtrip latency unnecessary for streaming time-series monitoring. |

---

## 3. Retained Messages for Machine Status

The `factory/{plant_id}/{machine_id}/status` topic uses `retain=True`.
- **Why?** When a new UI client, backend pod, or worker connects to the broker, it receives the latest machine state immediately without waiting for the next periodic publish cycle.
