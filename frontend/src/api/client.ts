import {
  Machine,
  TelemetryPoint,
  Alert,
  DigitalTwin,
  PlantSummary,
  SystemHealth,
  FaultScenario,
} from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

async function fetchJSON<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error [${response.status}]: ${errorBody}`);
  }

  return response.json();
}

export const api = {
  // System Health
  getHealth: () => fetchJSON<SystemHealth>('/health'),

  // Machines
  getMachines: () => fetchJSON<Machine[]>('/machines'),
  getMachine: (id: string) => fetchJSON<Machine>(`/machines/${id}`),

  // Telemetry
  getLatestTelemetry: (id: string) => fetchJSON<TelemetryPoint>(`/machines/${id}/telemetry/latest`),
  getTelemetryHistory: (id: string, limit = 60) =>
    fetchJSON<TelemetryPoint[]>(`/machines/${id}/telemetry/history?limit=${limit}`),

  // Digital Twin
  getDigitalTwin: (id: string) => fetchJSON<DigitalTwin>(`/machines/${id}/digital-twin`),

  // Alerts
  getAlerts: (machineId?: string) =>
    fetchJSON<Alert[]>(`/alerts${machineId ? `?machine_id=${machineId}` : ''}`),
  acknowledgeAlert: (alertId: string, operator: string) =>
    fetchJSON<Alert>(`/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ acknowledged_by: operator }),
    }),
  resolveAlert: (alertId: string) =>
    fetchJSON<Alert>(`/alerts/${alertId}/resolve`, { method: 'POST' }),

  // Analytics
  getPlantSummary: () => fetchJSON<PlantSummary>('/analytics/summary'),
  getMachineOEE: (id: string) => fetchJSON<any>(`/analytics/oee/${id}`),

  // Simulation & Fault Injection
  getFaultScenarios: () => fetchJSON<FaultScenario[]>('/simulation/scenarios'),
  injectFault: (machineId: string, faultName: string) =>
    fetchJSON<{ status: string; message: string; details?: any }>('/simulation/inject-failure', {
      method: 'POST',
      body: JSON.stringify({ machine_id: machineId, fault_name: faultName }),
    }),
  clearFault: (machineId: string) =>
    fetchJSON<{ status: string; message: string }>(`/simulation/clear-failure/${machineId}`, {
      method: 'POST',
    }),
};
