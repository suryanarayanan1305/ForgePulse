# FORGEPULSE: Database Architecture & SQL Design

## 1. Relational Schema Entity Relationship

```
┌──────────────┐          ┌──────────────────────┐          ┌────────────────────┐
│    PLANTS    │ 1      * │       MACHINES       │ 1      * │  MACHINE_SENSORS   │
│──────────────│──────────│──────────────────────│──────────│────────────────────│
│ PK plant_id  │          │ PK machine_id        │          │ PK sensor_id       │
│    name      │          │ FK plant_id          │          │ FK machine_id      │
│    location  │          │    type (CNC, PRESS) │          │    sensor_type     │
│    timezone  │          │    temp_limit        │          │    unit            │
└──────────────┘          │    vib_limit         │          │    min/max normal  │
                          │    status            │          └────────────────────┘
                          │    last_seen_at      │
                          └──────────┬───────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │ 1                     1 │                       1 │
           ▼ *                       ▼ *                       ▼ *
┌────────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│     TELEMETRY      │     │      ALERTS       │     │   DOWNTIME_LOGS   │
│────────────────────│     │───────────────────│     │───────────────────│
│ PK telemetry_id    │     │ PK alert_id       │     │ PK downtime_id    │
│ FK machine_id      │     │ FK machine_id     │     │ FK machine_id     │
│    timestamp (TZ)  │     │    alert_type     │     │    reason         │
│    temperature     │     │    severity       │     │    started_at     │
│    vibration       │     │    observed_value │     │    ended_at       │
│    pressure        │     │    threshold_value│     │    duration_sec   │
│    rpm             │     │    status         │     │    (GENERATED)    │
│    is_anomaly      │     │    cooldown_exp   │     └───────────────────┘
└────────────────────┘     └───────────────────┘
```

---

## 2. Key Indexing Design Decisions

### Primary Hot Path Query:
```sql
SELECT * FROM telemetry 
WHERE machine_id = 'CNC-001' 
ORDER BY timestamp DESC 
LIMIT 60;
```
**Index Applied**:
```sql
CREATE INDEX idx_telemetry_machine_time 
ON telemetry (machine_id, timestamp DESC);
```
*Why?* Enables an **Index Backward Scan** directly matching the filter and ordering clauses in a single step, avoiding sequential heap scans on millions of rows.

### Generated Column for Zero-Overhead Downtime Calculation:
```sql
duration_seconds INTEGER GENERATED ALWAYS AS (
    CASE 
        WHEN ended_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (ended_at - started_at))::INTEGER 
        ELSE NULL 
    END
) STORED;
```
*Why?* The database automatically computes and persists duration upon closure. Guarantees consistency between application code and database queries.
