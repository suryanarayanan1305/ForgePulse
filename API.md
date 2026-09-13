# FORGEPULSE: REST API Reference

All routes are versioned under `/api/v1/`.

## Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Overall system diagnostics (DB latency, MQTT status, message counts). |
| `GET` | `/api/v1/machines` | List all active shop-floor machines with limits and current status. |
| `GET` | `/api/v1/machines/{id}` | Get detailed machine metadata and configured sensor specifications. |
| `GET` | `/api/v1/machines/{id}/telemetry/latest` | Most recent sensor reading. |
| `GET` | `/api/v1/machines/{id}/telemetry/history` | Chronological time-series points for charting (supports `?limit=N`). |
| `GET` | `/api/v1/machines/{id}/digital-twin` | Unified digital twin (Identity + Live metrics + Health breakdown + Maintenance risk + Active alerts). |
| `GET` | `/api/v1/alerts` | List currently open operational alerts (supports `?machine_id=X`). |
| `POST`| `/api/v1/alerts/{id}/acknowledge` | Mark an alert as acknowledged by an operator. |
| `POST`| `/api/v1/alerts/{id}/resolve` | Mark an alert as resolved. |
| `GET` | `/api/v1/analytics/summary` | Top-level plant KPIs (Machine counts, OEE, Average Health). |
| `GET` | `/api/v1/analytics/oee/{id}` | 24-hour Availability, Performance, Quality, and OEE metrics. |
| `GET` | `/api/v1/analytics/trends/{id}/{metric}` | Historical trend points with limit line metadata. |
| `GET` | `/api/v1/simulation/scenarios` | List available deterministic fault injection scenarios. |
| `POST`| `/api/v1/simulation/inject-failure` | Inject fault scenario into target machine (`OVERHEATING`, `HIGH_VIBRATION`, etc.). |
| `POST`| `/api/v1/simulation/clear-failure/{id}` | Clear active fault scenario. |
