-- =============================================================================
-- FORGEPULSE: Industrial IoT Platform
-- Database Schema — PostgreSQL 16
--
-- Design Principles:
--   1. Core telemetry fields are relational columns (not JSON) for SQL analytics.
--   2. All timestamps are UTC TIMESTAMPTZ to handle multi-timezone plant networks.
--   3. Composite indexes on (machine_id, timestamp DESC) optimize the most common
--      time-series query pattern in telemetry-heavy workloads.
--   4. JSONB is used ONLY for flexible, variable-structure event metadata.
--   5. Soft deletes (is_active flag) preserve audit trails.
--
-- Schema:
--   plants               → A manufacturing facility / site
--   machines             → Physical (simulated) machines on the shop floor
--   machine_sensors      → Sensor specifications per machine
--   telemetry            → Periodic telemetry readings from machines
--   machine_events       → State changes, faults, restarts (event log)
--   alerts               → Generated anomaly/threshold alerts with lifecycle
--   downtime_logs        → Calculated downtime periods per machine
--   maintenance_records  → Maintenance work orders and inspection records
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Extensions
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- For uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";  -- Query profiling in prod

-- -----------------------------------------------------------------------------
-- PLANTS
-- A manufacturing plant / facility. ForgePulse supports multi-plant topology.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plants (
    plant_id        VARCHAR(50)     PRIMARY KEY,                        -- e.g., 'PLANT-A'
    plant_name      VARCHAR(200)    NOT NULL,
    location        VARCHAR(200)    NOT NULL,
    city            VARCHAR(100),
    country         VARCHAR(100)    NOT NULL DEFAULT 'India',
    timezone        VARCHAR(50)     NOT NULL DEFAULT 'Asia/Kolkata',
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE plants IS 'Manufacturing plants / facilities. Supports multi-site topology.';

-- -----------------------------------------------------------------------------
-- MACHINES
-- Individual machines on the shop floor. Simulation counterpart of physical
-- CNC, press, and milling assets.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS machines (
    machine_id          VARCHAR(50)     PRIMARY KEY,                    -- e.g., 'CNC-001'
    machine_name        VARCHAR(200)    NOT NULL,
    machine_type        VARCHAR(100)    NOT NULL,                       -- 'CNC', 'PRESS', 'MILL'
    plant_id            VARCHAR(50)     NOT NULL REFERENCES plants(plant_id) ON DELETE RESTRICT,
    location            VARCHAR(200),                                   -- Shop floor zone, e.g., 'Bay-3'
    manufacturer        VARCHAR(200),
    model               VARCHAR(200),
    serial_number       VARCHAR(100),
    installation_date   DATE,

    -- Operating limits — used by anomaly detection & health score
    rated_rpm           NUMERIC(10, 2),
    temperature_limit   NUMERIC(6, 2)   NOT NULL DEFAULT 85.0,         -- °C
    vibration_limit     NUMERIC(6, 2)   NOT NULL DEFAULT 8.0,          -- mm/s RMS
    pressure_limit      NUMERIC(6, 2)   NOT NULL DEFAULT 12.0,         -- bar
    power_limit         NUMERIC(8, 2),                                  -- kW

    -- Current operational state — updated by the MQTT ingestion worker
    current_status      VARCHAR(50)     NOT NULL DEFAULT 'STOPPED',    -- RUNNING, STOPPED, MAINTENANCE, FAULT
    last_seen_at        TIMESTAMPTZ,                                    -- Timestamp of last telemetry received
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE machines IS 'Shop floor machines. Reflects simulated physical assets.';
COMMENT ON COLUMN machines.current_status IS 'Kept up-to-date by MQTT ingestion worker on every telemetry message.';
COMMENT ON COLUMN machines.last_seen_at IS 'Used by diagnostics to detect stale/dead machines.';

-- Partial index for fast active-machine queries
CREATE INDEX IF NOT EXISTS idx_machines_plant_active
    ON machines (plant_id)
    WHERE is_active = TRUE;

-- -----------------------------------------------------------------------------
-- MACHINE SENSORS
-- Describes each sensor on a machine and its expected operating range.
-- Allows per-sensor threshold configuration instead of machine-wide limits.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS machine_sensors (
    sensor_id       UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id      VARCHAR(50)     NOT NULL REFERENCES machines(machine_id) ON DELETE CASCADE,
    sensor_type     VARCHAR(100)    NOT NULL,           -- 'TEMPERATURE', 'VIBRATION', 'PRESSURE', 'RPM'
    sensor_name     VARCHAR(200)    NOT NULL,
    unit            VARCHAR(50)     NOT NULL,           -- '°C', 'mm/s', 'bar', 'RPM', 'kW'
    min_normal      NUMERIC(10, 4),
    max_normal      NUMERIC(10, 4),
    critical_limit  NUMERIC(10, 4),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE machine_sensors IS 'Sensor specifications per machine with normal operating ranges.';
CREATE INDEX IF NOT EXISTS idx_machine_sensors_machine ON machine_sensors (machine_id);

-- -----------------------------------------------------------------------------
-- TELEMETRY
-- The highest-volume table. Stores every periodic reading from every machine.
-- At 1 reading/second × 5 machines = 432,000 rows/day.
--
-- CRITICAL DESIGN DECISION:
--   temperature, vibration, pressure, rpm are RELATIONAL COLUMNS — not JSON.
--   Reason: SQL aggregate functions (AVG, MAX, STDDEV, percentile_cont) require
--   native numeric types. Storing these inside JSON would require CAST on every
--   query, destroying index efficiency.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS telemetry (
    telemetry_id        UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id          VARCHAR(50)     NOT NULL REFERENCES machines(machine_id) ON DELETE CASCADE,
    plant_id            VARCHAR(50)     NOT NULL,

    -- Core sensor readings — all relational numeric columns for SQL analytics
    timestamp           TIMESTAMPTZ     NOT NULL,
    temperature         NUMERIC(6, 2),                  -- °C
    pressure            NUMERIC(6, 2),                  -- bar
    vibration           NUMERIC(6, 3),                  -- mm/s RMS
    rpm                 NUMERIC(8, 2),                  -- Revolutions Per Minute
    power_consumption   NUMERIC(8, 3),                  -- kW
    production_count    INTEGER         DEFAULT 0,       -- Parts produced (cumulative per session)
    machine_status      VARCHAR(50),                    -- RUNNING, STOPPED, MAINTENANCE, FAULT
    error_code          VARCHAR(50),                    -- NULL = no error, else: E001, E002, ...

    -- Anomaly detection flags — set by the backend ingestion worker
    is_anomaly          BOOLEAN         NOT NULL DEFAULT FALSE,
    anomaly_score       NUMERIC(5, 4),                  -- IsolationForest score (-1 to 1)

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE telemetry IS 'Time-series machine telemetry. Highest-volume table. Core metric fields are relational for SQL analytics.';

-- PRIMARY HOT PATH INDEX: (machine_id, timestamp DESC)
-- Optimizes the most common query: "latest N readings for machine X"
CREATE INDEX IF NOT EXISTS idx_telemetry_machine_time
    ON telemetry (machine_id, timestamp DESC);

-- ANALYTICS INDEX: Timestamp-only for plant-wide time-range queries
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp
    ON telemetry (timestamp DESC);

-- ANOMALY QUERY INDEX: Fast retrieval of anomalous readings per machine
CREATE INDEX IF NOT EXISTS idx_telemetry_anomaly
    ON telemetry (machine_id, is_anomaly)
    WHERE is_anomaly = TRUE;

-- -----------------------------------------------------------------------------
-- MACHINE EVENTS
-- Event log for state transitions, fault injections, restarts, acknowledgments.
-- Metadata uses JSONB because event payload structure varies per event type.
-- For example:
--   FAULT_INJECTED: {fault_type: "OVERHEATING", injected_by: "user", ...}
--   STATUS_CHANGE:  {from: "RUNNING", to: "STOPPED", triggered_by: "threshold"}
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS machine_events (
    event_id        UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id      VARCHAR(50)     NOT NULL REFERENCES machines(machine_id) ON DELETE CASCADE,
    event_type      VARCHAR(100)    NOT NULL,   -- STATUS_CHANGE, FAULT_INJECTED, RESET, MAINTENANCE_START
    severity        VARCHAR(20)     NOT NULL DEFAULT 'INFO',   -- INFO, WARNING, CRITICAL
    message         TEXT            NOT NULL,
    metadata        JSONB           DEFAULT '{}',              -- Variable structure per event type
    timestamp       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE machine_events IS 'Event log for state changes, faults, and operator actions. JSONB metadata for flexible payload.';
CREATE INDEX IF NOT EXISTS idx_machine_events_machine_time
    ON machine_events (machine_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_machine_events_type
    ON machine_events (event_type, timestamp DESC);
-- GIN index for JSONB queries on metadata
CREATE INDEX IF NOT EXISTS idx_machine_events_metadata
    ON machine_events USING GIN (metadata);

-- -----------------------------------------------------------------------------
-- ALERTS
-- Generated by the anomaly detection engine and alert service.
-- Implements full lifecycle: OPEN → ACKNOWLEDGED → RESOLVED.
-- The cooldown_expires_at field supports deduplication/alert suppression logic.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    alert_id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id          VARCHAR(50)     NOT NULL REFERENCES machines(machine_id) ON DELETE CASCADE,

    -- Alert classification
    alert_type          VARCHAR(100)    NOT NULL,   -- HIGH_TEMPERATURE, HIGH_VIBRATION, PRESSURE_ANOMALY
    severity            VARCHAR(20)     NOT NULL,   -- INFO, WARNING, CRITICAL
    message             TEXT            NOT NULL,

    -- Triggering metric details
    metric_name         VARCHAR(100),               -- 'temperature', 'vibration', 'pressure'
    observed_value      NUMERIC(10, 4),             -- Actual reading at time of alert
    threshold_value     NUMERIC(10, 4),             -- Configured limit that was breached

    -- Alert lifecycle
    status              VARCHAR(20)     NOT NULL DEFAULT 'OPEN',    -- OPEN, ACKNOWLEDGED, RESOLVED
    acknowledged_at     TIMESTAMPTZ,
    acknowledged_by     VARCHAR(200),
    resolved_at         TIMESTAMPTZ,

    -- Deduplication: prevents alert storms on persistent anomalies
    -- While cooldown_expires_at > NOW(), suppress re-generation of the same alert type
    cooldown_expires_at TIMESTAMPTZ,

    timestamp           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE alerts IS 'Alert lifecycle management. cooldown_expires_at implements deduplication to suppress alert storms.';
CREATE INDEX IF NOT EXISTS idx_alerts_machine_time
    ON alerts (machine_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_status
    ON alerts (status, timestamp DESC)
    WHERE status = 'OPEN';
CREATE INDEX IF NOT EXISTS idx_alerts_severity
    ON alerts (severity, timestamp DESC);

-- -----------------------------------------------------------------------------
-- DOWNTIME LOGS
-- Records discrete downtime periods per machine.
-- The MQTT ingestion worker creates a new record when a machine transitions from
-- RUNNING → STOPPED/FAULT/MAINTENANCE and closes it when it returns to RUNNING.
-- Duration is calculated as: (ended_at - started_at)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS downtime_logs (
    downtime_id     UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id      VARCHAR(50)     NOT NULL REFERENCES machines(machine_id) ON DELETE CASCADE,
    reason          VARCHAR(200),                           -- PLANNED, UNPLANNED, FAULT, MAINTENANCE
    reason_code     VARCHAR(50),                            -- E001, E002, PLANNED_MAINT, etc.
    started_at      TIMESTAMPTZ     NOT NULL,
    ended_at        TIMESTAMPTZ,                            -- NULL = machine is currently down
    duration_seconds INTEGER GENERATED ALWAYS AS (
        CASE
            WHEN ended_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (ended_at - started_at))::INTEGER
            ELSE NULL
        END
    ) STORED,                                               -- Computed column — auto-calculated
    notes           TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE downtime_logs IS 'Discrete downtime periods. duration_seconds is a generated (computed) column for analytics efficiency.';
CREATE INDEX IF NOT EXISTS idx_downtime_machine_time
    ON downtime_logs (machine_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_downtime_open
    ON downtime_logs (machine_id)
    WHERE ended_at IS NULL;     -- Fast lookup for "is this machine currently down?"

-- -----------------------------------------------------------------------------
-- MAINTENANCE RECORDS
-- Work orders, inspections, and completed maintenance activities.
-- Links to the alert or event that triggered the maintenance.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance_records (
    record_id           UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id          VARCHAR(50)     NOT NULL REFERENCES machines(machine_id) ON DELETE CASCADE,
    triggered_by_alert  UUID            REFERENCES alerts(alert_id) ON DELETE SET NULL,

    record_type         VARCHAR(100)    NOT NULL,   -- INSPECTION, REPAIR, REPLACEMENT, CALIBRATION
    description         TEXT            NOT NULL,
    status              VARCHAR(50)     NOT NULL DEFAULT 'SCHEDULED', -- SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED

    -- Risk score from the predictive maintenance engine at time of work order creation
    risk_score          NUMERIC(5, 2),              -- 0.0 to 100.0 — prototype only
    risk_level          VARCHAR(20),                -- LOW, MEDIUM, HIGH, CRITICAL

    scheduled_at        TIMESTAMPTZ,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,

    technician          VARCHAR(200),
    notes               TEXT,
    parts_replaced      JSONB           DEFAULT '[]',   -- [{part_name, part_number, cost}, ...]

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE maintenance_records IS 'Maintenance work orders. risk_score reflects prototype predictive maintenance output.';
CREATE INDEX IF NOT EXISTS idx_maintenance_machine
    ON maintenance_records (machine_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_maintenance_status
    ON maintenance_records (status)
    WHERE status IN ('SCHEDULED', 'IN_PROGRESS');

-- =============================================================================
-- TRIGGERS: auto-update updated_at timestamps
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_plants_updated_at
    BEFORE UPDATE ON plants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_machines_updated_at
    BEFORE UPDATE ON machines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_alerts_updated_at
    BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_downtime_updated_at
    BEFORE UPDATE ON downtime_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_maintenance_updated_at
    BEFORE UPDATE ON maintenance_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
