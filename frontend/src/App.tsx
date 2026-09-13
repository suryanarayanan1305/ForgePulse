import React, { useState, useEffect, useCallback } from 'react';
import { api } from './api/client';
import { Header } from './components/Header';
import { DiagnosticsBar } from './components/DiagnosticsBar';
import { FleetOverview } from './components/FleetOverview';
import { MachineCard } from './components/MachineCard';
import { LiveTelemetryChart } from './components/LiveTelemetryChart';
import { AlertsFeed } from './components/AlertsFeed';
import { DigitalTwinModal } from './components/DigitalTwinModal';
import { FaultInjectorModal } from './components/FaultInjectorModal';
import { Machine, TelemetryPoint, Alert, PlantSummary, SystemHealth } from './types';

export const App: React.FC = () => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [telemetryMap, setTelemetryMap] = useState<Record<string, TelemetryPoint>>({});
  const [selectedMachineId, setSelectedMachineId] = useState<string>('CNC-001');
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryPoint[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [plantSummary, setPlantSummary] = useState<PlantSummary | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [activeTwinId, setActiveTwinId] = useState<string | null>(null);
  const [isFaultModalOpen, setIsFaultModalOpen] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Fetch initial fleet and static metadata
  const loadInitialData = useCallback(async () => {
    try {
      const machineList = await api.getMachines();
      setMachines(machineList);
      if (machineList.length > 0 && !selectedMachineId) {
        setSelectedMachineId(machineList[0].machine_id);
      }
    } catch (err) {
      console.error('Failed to load machines', err);
    }
  }, [selectedMachineId]);

  // Fast polling loop for live metrics (every 2 seconds)
  const pollLiveData = useCallback(async () => {
    try {
      setIsRefreshing(true);
      const [healthData, summaryData, alertsData] = await Promise.all([
        api.getHealth().catch(() => null),
        api.getPlantSummary().catch(() => null),
        api.getAlerts().catch(() => []),
      ]);

      if (healthData) setSystemHealth(healthData);
      if (summaryData) setPlantSummary(summaryData);
      setAlerts(alertsData);

      // Fetch latest telemetry for all machines
      if (machines.length > 0) {
        const telemPromises = machines.map(async (m) => {
          try {
            const pt = await api.getLatestTelemetry(m.machine_id);
            return { id: m.machine_id, pt };
          } catch {
            return { id: m.machine_id, pt: null };
          }
        });
        const telemResults = await Promise.all(telemPromises);
        const newMap: Record<string, TelemetryPoint> = {};
        telemResults.forEach((r) => {
          if (r.pt) newMap[r.id] = r.pt;
        });
        setTelemetryMap((prev) => ({ ...prev, ...newMap }));
      }

      // Fetch history for selected machine
      if (selectedMachineId) {
        const history = await api.getTelemetryHistory(selectedMachineId, 40).catch(() => []);
        setTelemetryHistory(history);
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [machines, selectedMachineId]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  useEffect(() => {
    pollLiveData();
    const interval = setInterval(pollLiveData, 2000);
    return () => clearInterval(interval);
  }, [pollLiveData]);

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await api.acknowledgeAlert(alertId, 'ControlRoom_Op');
      pollLiveData();
    } catch (err) {
      console.error('Failed to acknowledge alert', err);
    }
  };

  const handleResolveAlert = async (alertId: string) => {
    try {
      await api.resolveAlert(alertId);
      pollLiveData();
    } catch (err) {
      console.error('Failed to resolve alert', err);
    }
  };

  const selectedMachine = machines.find((m) => m.machine_id === selectedMachineId) || machines[0];

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans">
      <Header
        onRefresh={pollLiveData}
        isRefreshing={isRefreshing}
        onOpenFaultInjector={() => setIsFaultModalOpen(true)}
      />

      <DiagnosticsBar health={systemHealth} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-6 space-y-6">
        {/* Fleet KPI Banner */}
        <FleetOverview summary={plantSummary} />

        {/* Machine Digital Twin Fleet Grid */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">
              Shop Floor Digital Twins & Fleet Status
            </h2>
            <span className="text-xs text-slate-500 font-mono">
              Click machine card to inspect live telemetry
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {machines.map((machine) => (
              <MachineCard
                key={machine.machine_id}
                machine={machine}
                latestTelemetry={telemetryMap[machine.machine_id]}
                isSelected={selectedMachineId === machine.machine_id}
                onSelect={(id) => setSelectedMachineId(id)}
                onOpenTwin={(id) => setActiveTwinId(id)}
              />
            ))}
          </div>
        </div>

        {/* Real-time Telemetry Trends & Operational Alerts Feed */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            {selectedMachine && (
              <LiveTelemetryChart machine={selectedMachine} history={telemetryHistory} />
            )}
          </div>
          <div className="lg:col-span-1">
            <AlertsFeed
              alerts={alerts}
              onAcknowledge={handleAcknowledgeAlert}
              onResolve={handleResolveAlert}
            />
          </div>
        </div>
      </main>

      {/* Modals */}
      <DigitalTwinModal machineId={activeTwinId} onClose={() => setActiveTwinId(null)} />
      <FaultInjectorModal
        isOpen={isFaultModalOpen}
        machines={machines}
        onClose={() => setIsFaultModalOpen(false)}
        onFaultInjected={pollLiveData}
      />
    </div>
  );
};

export default App;
