# FORGEPULSE: Forward Deployed Engineer (FDE) Master Interview Guide

This guide prepares you to explain and defend every technical decision in **ForgePulse** for your interview at **TVS NEXT**.

---

## Part 1: Project Pitches

### 1. The 30-Second Elevator Pitch
> "ForgePulse is an end-to-end Industrial IoT and Digital Twin platform for manufacturing shop floors. It simulates CNC and hydraulic machinery physics, scales sensor tags through a Software PLC layer, streams telemetry over MQTT with QoS 1, ingests and validates payloads asynchronously in FastAPI, detects anomalies using a 3-tier engine (thresholds, statistical Z-scores, and Isolation Forest ML), calculates Overall Equipment Effectiveness (OEE) and downtime transitions in PostgreSQL, and presents live operations and digital twins in a React dashboard with interactive failure injection capabilities."

### 2. The 1-Minute Pitch
> "In manufacturing, unplanned downtime and silent bearing failures cost millions. I built ForgePulse to represent the complete industrial data highway: from physical asset dynamics, through PLC 4-20mA scaling, edge MQTT gateways, up to cloud processing and real-time operations dashboards.
> 
> The platform features a modular monolith backend with FastAPI and PostgreSQL 16, indexing telemetry with composite B-Tree indexes for sub-5ms lookups. It features a transparent health scoring algorithm, multi-tier anomaly detection that catches both extreme spikes and subtle multivariate pattern drifts, and automated alert cooldowns to prevent alert fatigue. An interactive failure injection console allows operators to simulate coolant failure or bearing wear and watch the closed-loop alerting and health degradation in real time."

### 3. The 3-Minute Deep Dive
> "The architecture solves four fundamental industrial engineering challenges:
> 
> 1. **Data Ingestion & Network Resilience**: Industrial edge networks are unreliable. Using MQTT over TCP with QoS 1 guarantees message delivery. My backend ingestion worker runs on a dedicated async event loop bridge with persistent sessions and auto-reconnect backoff.
> 2. **Data Integrity & Schema Guarding**: Rather than dumping unvalidated JSON into a NoSQL store, telemetry is validated using Pydantic V2 and stored in strongly-typed relational PostgreSQL columns with B-Tree indexes on `(machine_id, timestamp DESC)`. This enables sub-millisecond aggregations for rolling OEE metrics.
> 3. **Observability & Explainable AI**: Black-box ML models are rejected by shop-floor plant managers. ForgePulse uses a transparent health score formula with explicit penalty breakdowns, paired with a 3-tier anomaly detector: static engineering limits, rolling Z-score statistical tests, and lightweight Scikit-Learn IsolationForest models.
> 4. **Closed-Loop Operational Feedback**: Using the interactive fault injection API, an engineer can inject overheating or mechanical imbalance on a CNC asset. Within 2 seconds, the simulator alters physics, the PLC rescales tags, MQTT publishes abnormal frames, the backend flags the anomaly, logs a deduplicated alert, transitions downtime states, and updates the digital twin and operations UI."

---

## Part 2: Technical Defense & Deep-Dive Q&A

### 4. Why Python?
- Dominates the Industrial IoT and data engineering landscape.
- Provides standard numerical and ML libraries (`NumPy`, `Pandas`, `Scikit-Learn`).
- Standard language for Forward Deployed Engineers who bridge backend software, edge scripting, and analytics.

### 5. Why FastAPI?
- Native asynchronous ASGI execution matching async database drivers (`asyncpg`).
- Strict schema validation and serialization using Pydantic V2.
- Automatic OpenAPI / Swagger documentation generation out of the box.

### 6. Why PostgreSQL instead of MongoDB or InfluxDB?
- Core manufacturing workflows require **strict relational integrity** (foreign keys between plants, machines, sensors, alerts, downtime logs, and work orders).
- Analytical aggregation functions (`AVG`, `MAX`, `STDDEV`, window functions) run with high performance on relational numeric columns with composite B-Tree indexes on `(machine_id, timestamp DESC)`.
- Flexible event payloads are supported using native `JSONB` columns with GIN indexes.

### 7. Why MQTT instead of HTTP Polling for Telemetry?
- **Packet Overhead**: MQTT packet headers are only 2 bytes, compared to kilobytes of HTTP headers on bandwidth-constrained industrial gateway networks.
- **Decoupled Topology**: Publishers (machines) and subscribers (backend workers, dashboard listeners) are completely decoupled via broker topics.
- **Quality of Service (QoS 1)**: Guarantees delivery even over intermittent shop-floor cellular/Wi-Fi links.

### 8. What is the role of the MQTT Broker?
- Acts as the central message router.
- Dispatches messages to subscribed topics, manages client connection sessions, queues QoS 1 unacknowledged packets, and maintains retained messages.

### 9. Publisher vs Subscriber?
- **Publisher**: Edge gateway reading PLC registers and publishing telemetry payloads.
- **Subscriber**: Backend ingestion service listening to wildcard topics (`factory/+/+/telemetry`).

### 10. How does telemetry reach the database?
- Machine Physics $\rightarrow$ PLC Tag Table $\rightarrow$ Paho MQTT Publisher $\rightarrow$ Mosquitto Broker $\rightarrow$ Backend Subscriber Worker $\rightarrow$ Pydantic Validation $\rightarrow$ Multi-Tier Anomaly Check $\rightarrow$ Async SQLAlchemy Session $\rightarrow$ PostgreSQL Table `telemetry`.

### 11. What is a Digital Twin in ForgePulse?
- A unified software entity that aggregates static design limits, real-time sensor metrics, historical trends, transparent health breakdowns, active alerts, and prototype maintenance-risk estimates into a single queryable payload (`GET /api/v1/machines/{id}/digital-twin`).

### 12. How is Machine Health calculated?
$$\text{Health} = 100 - (\text{Temp\_Pen} + \text{Vib\_Pen} + \text{Pres\_Pen} + \text{Err\_Pen} + \text{Downtime\_Pen})$$
- Fully deterministic, transparent, and explainable to shop-floor plant managers.

### 13. How does Anomaly Detection work?
- **Level 1**: Static threshold comparison against machine engineering limits.
- **Level 2**: Rolling statistical Z-Score ($|Z| = |(x - \mu) / \sigma| > 3.0$) over recent 50-sample sliding windows.
- **Level 3**: Multivariate unsupervised `IsolationForest` across `[temperature, vibration, pressure, rpm, power]`.

### 14. How does Predictive Maintenance risk estimation work?
- Prototype maintenance-risk estimator that weights multi-signal degradation: rising vibration trends, baseline thermal elevation, persistent open alerts, and active fault states to provide risk percentages and actionable inspection recommendations.

### 15. What happens if the MQTT Broker goes down?
- The simulator publisher and backend subscriber catch disconnect events and enter an automatic exponential backoff reconnection loop.
- Messages published with QoS 1 are queued and transmitted as soon as the broker connection is restored.

### 16. What happens if PostgreSQL goes down?
- Connection pool `pool_pre_ping=True` detects lost connections.
- Ingestion worker logs the error with structured JSON metadata (`TELEMETRY_DB_ERROR`) without crashing the FastAPI application process.
- The `/api/v1/health` endpoint reports degraded database status.

### 17. How did you handle malformed telemetry?
- Incoming MQTT strings pass through `TelemetryIngest.model_validate()`.
- Invalid JSON or out-of-bound sensor values trigger validation errors that are logged with payload previews while the worker continues processing subsequent messages without interruption.

### 18. How did you prevent duplicate alerts (Alert Storms)?
- `AlertService` checks `cooldown_expires_at > NOW()`. If an unexpired open alert of the same type exists for that machine, duplicate alert generation is suppressed in memory.

### 19. How did you calculate Downtime?
- State transitions (`RUNNING` $\rightarrow$ `STOPPED`/`FAULT`) insert an open `DowntimeLog` record.
- Transition back to `RUNNING` sets `ended_at`.
- PostgreSQL automatically computes `duration_seconds` using a stored generated column: `EXTRACT(EPOCH FROM (ended_at - started_at))::INTEGER`.

### 20. How did you calculate OEE?
$$\text{OEE} = \text{Availability} \times \text{Performance} \times \text{Quality}$$
- Computed dynamically using SQL aggregations over rolling 24-hour windows.

### 21. Why Docker?
- Guarantees environment parity across local development, testing, and production deployment.
- Eliminates "it works on my machine" issues for multi-service dependencies (Postgres, Mosquitto, Python backend, React frontend).

### 22. How did you deploy it?
- Frontend: Vercel with automated continuous deployment from Git.
- Backend & Database: Render web service container paired with managed PostgreSQL.
- MQTT: Managed cloud broker (HiveMQ / EMQX Cloud) configured via environment variables.

### 23. What would you change for a 10,000-machine production deployment?
- Replace single-node Mosquitto with a clustered MQTT broker (EMQX Cluster / AWS IoT Core).
- Introduce **TimescaleDB** or Apache Kafka for high-throughput raw telemetry ingestion.
- Deploy Celery / Redis workers for asynchronous ML model re-fitting.
- Deploy onto Kubernetes with Horizontal Pod Autoscalers (HPA) driven by MQTT queue depth.

### 24. How would this connect to a real physical PLC?
- Replace `simulator/main.py` with an industrial edge connector speaking **OPC-UA** (`opcua-asyncio`) or **Modbus TCP** (`pymodbus`).
- The edge script reads PLC register blocks, converts raw counts to engineering units, and publishes the identical JSON payload to the MQTT broker.

### 25. How would this integrate with a Manufacturing Execution System (MES)?
- Expose bi-directional REST / Webhook endpoints for work order synchronization and production batch logging (`production_records`).

### 26. What was the hardest engineering problem you solved?
- Bridging the synchronous Paho-MQTT client networking thread with FastAPI's asynchronous `asyncio` event loop and SQLAlchemy connection pool without introducing thread deadlocks or dropping QoS 1 message frames.

### 27. What bug did you encounter and how did you resolve it?
- *Bug*: SQLAlchemy's `DeclarativeBase` threw an `InvalidRequestError: Attribute name 'metadata' is reserved` when defining `MachineEvent.metadata`.
- *Resolution*: Renamed the ORM attribute to `event_metadata` while mapping the underlying PostgreSQL column name as `"metadata"` via `mapped_column("metadata", JSONB, ...)`.
- *Bug*: Pydantic V2 prohibited leading underscore field names (`_plc_meta`).
- *Resolution*: Defined `plc_meta` with `Field(alias="_plc_meta")` and enabled `ConfigDict(populate_by_name=True)`.

### 28. How can you demonstrate this platform live in an interview?
1. Open the **Operations Dashboard** at `http://localhost:5173`.
2. Show all 5 machines operating in normal green status with live temperature and vibration graphs.
3. Click **"Inject Failure"** $\rightarrow$ select `CNC-001` $\rightarrow$ select `OVERHEATING`.
4. Observe the live temperature trend climbing past $85^\circ\text{C}$, the `HIGH_TEMPERATURE` alert appearing in the feed, the machine health score dropping from 95% to 61%, and the predictive maintenance recommendation changing to "Immediate inspection required".
5. Click **"Clear Faults"** and watch the asset return to nominal baseline.
