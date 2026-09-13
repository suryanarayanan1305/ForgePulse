# FORGEPULSE
### Industrial IoT, Digital Twin & Predictive Maintenance Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-660066?logo=eclipse-mosquitto&logoColor=white)](https://mosquitto.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)

---

> **Honest Engineering Disclaimer**:  
> ForgePulse is an end-to-end **manufacturing and industrial IoT simulation and monitoring platform**. It simulates machine physics, Software PLC tag registers, and industrial edge gateway communication for demonstration and testing purposes. It does not connect to real physical industrial PLC hardware or safety-critical control systems.

---

## 🏭 Overview & Problem Statement

Modern discrete and continuous manufacturing plants lose millions annually to unplanned machine downtime, silent bearing failures, and inaccurate Overall Equipment Effectiveness (OEE) tracking.

**FORGEPULSE** bridges physical shop-floor machinery and cloud analytics by modeling the complete industrial data highway:

```
[ Physical Machine Physics ]
           │
           ▼ (4-20mA Sensor Signals)
[ Software PLC Abstraction ]
           │
           ▼ (Engineering Unit Scaling & Tag Table)
[ IoT / Edge Gateway ]
           │
           ▼ (QoS 1 Telemetry Stream over Port 1883)
[ Mosquitto MQTT Broker ]
           │
           ▼ (Subscribed Topic: factory/plant-a/{machine_id}/telemetry)
[ FastAPI Ingestion Engine ]
           ├──► [ Pydantic Schema Validation & Sanitization ]
           ├──► [ Multi-Tier Anomaly Engine (Thresholds + Z-Score + IsolationForest) ]
           ├──► [ Deduplicated Alert Engine with Cooldown Windows ]
           └──► [ State Machine & Downtime Duration Tracker ]
           │
           ▼
[ PostgreSQL 16 Database ] (B-Tree Indexes on (machine_id, timestamp DESC))
           │
           ▼
[ Digital Twin Synthesis & Operational APIs ]
           │
           ▼ (HTTP / JSON / WebSockets)
[ Industrial Operations Center Dashboard (React + TypeScript + Recharts) ]
```

---

## ⚡ Key Features

- **Multi-Machine Physics Simulation Engine**: Simulates realistic thermal dissipation, RPM ramp acceleration, mechanical vibration spectrum, hydraulic pressure dynamics, and cumulative production counts across 5 assets: `CNC-001`, `CNC-002`, `CNC-003`, `PRESS-001`, and `MILL-001`.
- **Software PLC Tag Mapping**: Simulates 4-20mA analog signal transmitter scaling (`min + (mA-4)/16 * (max-min)`), scan cycle intervals, and OPC-UA signal quality indicators (`GOOD`, `BAD`, `UNCERTAIN`).
- **Resilient MQTT Pipeline**: QoS 1 "At Least Once" message delivery with automatic client reconnection and backpressure buffering.
- **Unified Digital Twin Model**: Merges static machine envelope limits, live telemetry readings, transparent health breakdowns, and prototype maintenance-risk predictions into a single queryable entity.
- **Transparent Health Score Formula**: `Health = 100 - (Temp_Pen + Vib_Pen + Pres_Pen + Err_Pen + Downtime_Pen)` with clear auditability (no opaque black box numbers).
- **Multi-Tier Anomaly Detection**:
  - *Level 1*: Hard static threshold limits.
  - *Level 2*: Rolling statistical Z-Score baseline detection ($|Z| > 3.0$).
  - *Level 3*: Multivariate unsupervised Machine Learning (`Scikit-Learn IsolationForest`).
- **Interactive Fault Injection Console**: Remotely trigger deterministic failure scenarios (`OVERHEATING`, `HIGH_VIBRATION`, `PRESSURE_SPIKE`, `MOTOR_OVERLOAD`, `MACHINE_STOP`) to prove the closed-loop alerting and dashboard update pipeline.
- **Production Analytics & OEE**: Dynamic calculations for Machine Availability, Performance efficiency, Quality yield, and overall OEE.

---

## 🚀 Quick Start (Local Docker Compose)

```bash
# 1. Clone repository
git clone https://github.com/your-username/forgepulse.git
cd forgepulse

# 2. Configure environment
cp .env.example .env

# 3. Start full platform stack (Postgres, Mosquitto, Backend, Simulator, Frontend)
docker compose --profile full up --build
```

Access the user interfaces:
- **Operations Dashboard**: `http://localhost:5173`
- **FastAPI OpenAPI Swagger**: `http://localhost:8000/docs`
- **System Health Diagnostics**: `http://localhost:8000/api/v1/health`

---

## 🧪 Running Automated Tests

```bash
# Run unit tests across anomaly detection, health scoring, and validation
python -m pytest backend/tests -v
```

---

## 📚 Complete Documentation Suite

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Deep technical blueprint & data lifecycle
- [`DATABASE.md`](DATABASE.md) — PostgreSQL DDL schema, indexing strategy & SQL queries
- [`MQTT.md`](MQTT.md) — Broker topic hierarchy, QoS choices & network resilience
- [`API.md`](API.md) — REST API specification & schemas
- [`ML.md`](ML.md) — IsolationForest, Z-Score formulas & health scoring mathematics
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — FDE incident response & debugging playbooks
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — Cloud deployment guide (Render + Vercel + Mosquitto)
- [`INTERVIEW_GUIDE.md`](INTERVIEW_GUIDE.md) — **34+ Forward Deployed Engineer interview questions & model answers**
