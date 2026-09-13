export interface Machine {
  machine_id: string;
  machine_name: str;
  machine_type: str;
  plant_id: str;
  location: string | null;
  manufacturer: string | null;
  model: string | null;
  rated_rpm: number | null;
  temperature_limit: number;
  vibration_limit: number;
  pressure_limit: number;
  power_limit: number | null;
  current_status: 'RUNNING' | 'STOPPED' | 'MAINTENANCE' | 'FAULT';
  last_seen_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TelemetryPoint {
  telemetry_id: string;
  machine_id: string;
  plant_id: string;
  timestamp: string;
  temperature: number | null;
  pressure: number | null;
  vibration: number | null;
  rpm: number | null;
  power_consumption: number | null;
  production_count: number;
  machine_status: string;
  error_code: string | null;
  is_anomaly: boolean;
  anomaly_score: number | null;
}

export interface Alert {
  alert_id: string;
  machine_id: string;
  alert_type: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  message: string;
  metric_name: string | null;
  observed_value: number | null;
  threshold_value: number | null;
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  timestamp: string;
}

export interface HealthBreakdown {
  overall_health: number;
  status_category: 'HEALTHY' | 'WARNING' | 'CRITICAL' | 'OFFLINE';
  temperature_penalty: number;
  vibration_penalty: number;
  pressure_penalty: number;
  error_penalty: number;
  downtime_penalty: number;
  formula_explanation: string;
}

export interface MaintenancePrediction {
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  signals: string[];
  recommendation: string;
  disclaimer: string;
}

export interface ProductionSummary {
  total_parts: number;
  operating_hours: number;
  downtime_minutes: number;
  current_run_duration_minutes: number;
}

export interface DigitalTwin {
  identity: Machine;
  current_status: string;
  health: HealthBreakdown;
  maintenance_prediction: MaintenancePrediction;
  production: ProductionSummary;
  latest_telemetry: TelemetryPoint | null;
  active_alerts: Alert[];
  last_seen: string | null;
  twin_timestamp: string;
}

export interface PlantSummary {
  total_machines: number;
  running_machines: number;
  stopped_machines: number;
  fault_machines: number;
  maintenance_machines: number;
  total_parts_produced: number;
  active_alerts_count: number;
  average_plant_health: number;
  plant_oee: number;
}

export interface SystemHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  timestamp: string;
  components: {
    api: { status: string; version: string };
    database: { status: string; latency_ms?: number; error?: string };
    mqtt_broker: { status: string; messages_received: number; last_message_seconds_ago?: number };
    telemetry_stream: { status: string; freshness_seconds?: number };
    analytics_engine: { status: string };
  };
}

export interface FaultScenario {
  fault_name: string;
  display_name: string;
  description: string;
  intensity: number;
  duration_seconds: number | null;
  expected_alerts: string[];
}
