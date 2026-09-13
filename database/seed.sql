-- =============================================================================
-- FORGEPULSE: Database Seed Data
-- Realistic manufacturing plant configuration for demonstration
--
-- Machines simulated:
--   CNC-001, CNC-002, CNC-003  → CNC Machining Centers (high-speed, precision)
--   PRESS-001                  → Hydraulic Press
--   MILL-001                   → Vertical Milling Machine
--
-- NOTE: This is SIMULATED data. No real factory or PLC is connected.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Plant / Facility
-- -----------------------------------------------------------------------------
INSERT INTO plants (plant_id, plant_name, location, city, country, timezone, is_active)
VALUES (
    'PLANT-A',
    'Chennai Advanced Manufacturing Facility',
    'SIPCOT Industrial Complex, Irungattukottai',
    'Chennai',
    'India',
    'Asia/Kolkata',
    TRUE
) ON CONFLICT (plant_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Machines — Simulated Shop Floor Assets
-- Operating limits are realistic values from industrial CNC/press documentation
-- -----------------------------------------------------------------------------
INSERT INTO machines (
    machine_id, machine_name, machine_type, plant_id, location,
    manufacturer, model, serial_number, installation_date,
    rated_rpm, temperature_limit, vibration_limit, pressure_limit, power_limit,
    current_status, is_active
) VALUES
-- CNC Machining Centers
(
    'CNC-001',
    'CNC Machining Center Alpha',
    'CNC',
    'PLANT-A',
    'Bay-1, Zone-A',
    'Haas Automation (Simulated)',
    'VF-2SS',
    'SIM-CNC-001-2022',
    '2022-03-15',
    8000,   -- rated RPM
    85.0,   -- temperature limit °C
    7.5,    -- vibration limit mm/s RMS
    10.0,   -- pressure limit bar
    22.0,   -- power limit kW
    'STOPPED',
    TRUE
),
(
    'CNC-002',
    'CNC Machining Center Beta',
    'CNC',
    'PLANT-A',
    'Bay-1, Zone-B',
    'Haas Automation (Simulated)',
    'VF-4',
    'SIM-CNC-002-2021',
    '2021-07-20',
    6000,
    82.0,
    7.0,
    10.0,
    30.0,
    'STOPPED',
    TRUE
),
(
    'CNC-003',
    'CNC Machining Center Gamma',
    'CNC',
    'PLANT-A',
    'Bay-2, Zone-A',
    'DMG Mori (Simulated)',
    'DMU 50',
    'SIM-CNC-003-2020',
    '2020-11-10',
    6000,
    80.0,
    7.0,
    9.5,
    25.0,
    'STOPPED',
    TRUE
),
-- Hydraulic Press
(
    'PRESS-001',
    'Hydraulic Press Station 1',
    'PRESS',
    'PLANT-A',
    'Bay-3, Zone-A',
    'Schuler AG (Simulated)',
    'MSP-500',
    'SIM-PRESS-001-2019',
    '2019-05-01',
    300,    -- rated RPM (slow hydraulic stroke)
    70.0,   -- hydraulic oil temperature limit °C
    5.0,    -- vibration limit mm/s RMS (presses vibrate less)
    250.0,  -- hydraulic pressure limit bar
    75.0,   -- power limit kW
    'STOPPED',
    TRUE
),
-- Vertical Milling Machine
(
    'MILL-001',
    'Vertical Milling Machine 1',
    'MILL',
    'PLANT-A',
    'Bay-2, Zone-B',
    'Bridgeport (Simulated)',
    'Series I',
    'SIM-MILL-001-2023',
    '2023-01-12',
    4000,
    75.0,
    6.5,
    8.0,
    15.0,
    'STOPPED',
    TRUE
) ON CONFLICT (machine_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Machine Sensors — specification per sensor per machine
-- -----------------------------------------------------------------------------
INSERT INTO machine_sensors (machine_id, sensor_type, sensor_name, unit, min_normal, max_normal, critical_limit)
VALUES
-- CNC-001
('CNC-001', 'TEMPERATURE', 'Spindle Temperature',        '°C',    20.0,  75.0,  85.0),
('CNC-001', 'VIBRATION',   'Spindle Vibration (X-axis)', 'mm/s',  0.0,   5.0,   7.5),
('CNC-001', 'PRESSURE',    'Coolant Pressure',           'bar',   2.0,   8.0,   10.0),
('CNC-001', 'RPM',         'Spindle Speed',              'RPM',   0.0,   8000,  8500),
('CNC-001', 'POWER',       'Motor Power Consumption',    'kW',    0.0,   18.0,  22.0),
-- CNC-002
('CNC-002', 'TEMPERATURE', 'Spindle Temperature',        '°C',    20.0,  72.0,  82.0),
('CNC-002', 'VIBRATION',   'Spindle Vibration (X-axis)', 'mm/s',  0.0,   5.0,   7.0),
('CNC-002', 'PRESSURE',    'Coolant Pressure',           'bar',   2.0,   8.0,   10.0),
('CNC-002', 'RPM',         'Spindle Speed',              'RPM',   0.0,   6000,  6500),
('CNC-002', 'POWER',       'Motor Power Consumption',    'kW',    0.0,   25.0,  30.0),
-- CNC-003
('CNC-003', 'TEMPERATURE', 'Spindle Temperature',        '°C',    20.0,  70.0,  80.0),
('CNC-003', 'VIBRATION',   'Spindle Vibration (X-axis)', 'mm/s',  0.0,   4.5,   7.0),
('CNC-003', 'PRESSURE',    'Coolant Pressure',           'bar',   2.0,   7.5,   9.5),
('CNC-003', 'RPM',         'Spindle Speed',              'RPM',   0.0,   6000,  6500),
('CNC-003', 'POWER',       'Motor Power Consumption',    'kW',    0.0,   20.0,  25.0),
-- PRESS-001
('PRESS-001', 'TEMPERATURE', 'Hydraulic Oil Temperature', '°C',   30.0,  60.0,  70.0),
('PRESS-001', 'VIBRATION',   'Frame Vibration',           'mm/s', 0.0,   3.0,   5.0),
('PRESS-001', 'PRESSURE',    'Hydraulic System Pressure', 'bar',  50.0,  220.0, 250.0),
('PRESS-001', 'RPM',         'Drive Motor Speed',         'RPM',  0.0,   300,   350),
('PRESS-001', 'POWER',       'Motor Power Consumption',   'kW',   0.0,   60.0,  75.0),
-- MILL-001
('MILL-001', 'TEMPERATURE', 'Spindle Bearing Temperature','°C',   20.0,  65.0,  75.0),
('MILL-001', 'VIBRATION',   'Table Vibration',            'mm/s', 0.0,   4.0,   6.5),
('MILL-001', 'PRESSURE',    'Coolant Pressure',           'bar',  1.5,   6.0,   8.0),
('MILL-001', 'RPM',         'Spindle Speed',              'RPM',  0.0,   4000,  4200),
('MILL-001', 'POWER',       'Motor Power Consumption',    'kW',   0.0,   12.0,  15.0)
ON CONFLICT DO NOTHING;
