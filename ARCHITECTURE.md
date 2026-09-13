# FORGEPULSE: System Architecture Blueprint

## 1. Architectural Style: Modular Monolith

ForgePulse is intentionally built as a **Modular Monolith** rather than a distributed set of microservices.

### Engineering Rationale:
- **Zero Network Serialization Overhead**: In-memory function dispatch between anomaly detectors, alert engine, and database persistence.
- **Transactional Consistency**: Single ACID transaction handles state transitions, downtime log closures, and telemetry persistence without distributed 2-phase commit overhead.
- **Operational Simplicity**: Easily containerized as a single deployable unit on edge gateways or cloud instances (Render).

---

## 2. End-to-End Component Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LAYER 1: SHOP FLOOR                              │
│                                                                             │
│  ┌───────────────────────┐                  ┌────────────────────────────┐  │
│  │    Machine Physics    │                  │        Software PLC        │  │
│  │ (Thermal Dissipation, │ ──4-20mA Signal─►│ (Scan Cycle: 1000ms,       │  │
│  │  RPM, Vibration Load) │                  │  Tag Table, Scaling Math)  │  │
│  └───────────────────────┘                  └────────────────────────────┘  │
│                                                            │                │
│                                                            ▼                │
│                                             ┌────────────────────────────┐  │
│                                             │     IoT / Edge Gateway     │  │
│                                             │ (Paho-MQTT Publisher,      │  │
│                                             │  QoS 1, ISO8601 Timestamps)│  │
│                                             └────────────────────────────┘  │
└────────────────────────────────────────────────────────────┬────────────────┘
                                                             │
                                                   MQTT over TCP (1883)
                                                             │
┌────────────────────────────────────────────────────────────▼────────────────┐
│                      LAYER 2: MESSAGING & INGESTION                         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     Eclipse Mosquitto Broker                          │  │
│  │ Topics: factory/plant-a/{machine_id}/telemetry                        │  │
│  │         factory/plant-a/{machine_id}/events                           │  │
│  │         factory/plant-a/{machine_id}/status (retained)                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                        Subscribed QoS 1 Stream                              │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                  Async Ingestion Worker Bridge                        │  │
│  │ (Paho MQTT Network Thread ──► Asyncio Event Loop ──► DB Context Pool) │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┬────────────────┘
                                                             │
┌────────────────────────────────────────────────────────────▼────────────────┐
│                         LAYER 3: BACKEND CORE                               │
│                                                                             │
│  ┌────────────────────┐   ┌──────────────────────┐   ┌───────────────────┐  │
│  │  Pydantic V2 Guard │──►│ Multi-Tier Detection │──►│   Alert Engine    │  │
│  │  (Schema Validate) │   │ (Thresholds + Z + ML)│   │ (Cooldown 300s)   │  │
│  └────────────────────┘   └──────────────────────┘   └───────────────────┘  │
│                                                                 │           │
│                                                                 ▼           │
│  ┌────────────────────┐   ┌──────────────────────┐   ┌───────────────────┐  │
│  │  State & Downtime  │   │  SQLAlchemy 2.0 ORM  │   │  PostgreSQL 16    │  │
│  │  (Transition Log)  │──►│  (Async Connection   │──►│  (B-Tree Indexes  │  │
│  │                    │   │   Pool, asyncpg)     │   │   on machine+time)│  │
│  └────────────────────┘   └──────────────────────┘   └───────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        FastAPI REST API Core                          │  │
│  │  Routes: /health, /machines, /telemetry, /digital-twin, /alerts,      │  │
│  │          /analytics/oee, /simulation/inject-failure                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┬────────────────┘
                                                             │
                                                        HTTP / JSON
                                                             │
┌────────────────────────────────────────────────────────────▼────────────────┐
│                       LAYER 4: PRESENTATION (UI)                            │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  React 18 + TypeScript + Tailwind CSS + Recharts                      │  │
│  │   - Real-time Fleet KPI Overview & Health Gauges                      │  │
│  │   - Shop Floor Digital Twin Cards                                     │  │
│  │   - Synchronized Live Telemetry Streaming Graphs                      │  │
│  │   - Interactive Fault Injector Console                                │  │
│  │   - Operational Alerts Feed with Acknowledgment Action                │  │
│  │   - Diagnostic System Health Status Bar                               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Tradeoff Matrix

| Decision | Selected Tech | Alternative Considered | Tradeoff Justification |
|---|---|---|---|
| **API Framework** | FastAPI (ASGI) | Flask (WSGI) / Django | Native asynchronous execution matches asyncpg; Pydantic V2 provides ultra-fast deserialization with zero boilerplate. |
| **Database** | PostgreSQL 16 | MongoDB / InfluxDB | Strong relational integrity (FKs across plants, machines, sensors, alerts) and B-Tree indexes on `(machine_id, timestamp DESC)`. |
| **Ingestion Protocol** | MQTT 3.1.1 (Mosquitto) | HTTP Polling / WebSockets | 2-byte header overhead vs kilobytes of HTTP headers; built-in QoS 1 delivery guarantees; standardized across industrial IoT gateways. |
| **Anomaly ML** | IsolationForest | Deep Learning (LSTM/Autoencoder) | Fast tabular unsupervised inference (<1ms); no GPU requirement; high interpretability for manufacturing operations. |
