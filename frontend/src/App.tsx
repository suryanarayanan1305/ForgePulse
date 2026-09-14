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
  const [isInitialLoad, setIsInitialLoad] = useState<boolean>(true);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const loadInitialData = useCallback(async () => {
    try {
      const machineList = await api.getMachines();
      setMachines(machineList);
      setConnectionError(null);
      if (machineList.length > 0 && !selectedMachineId) {
        setSelectedMachineId(machineList[0].machine_id);
      }
    } catch (err: any) {
      setConnectionError('Cannot reach backend API. Free Render instances spin down — please wait 30–60s for cold start.');
    } finally {
      setIsInitialLoad(false);
    }
  }, [selectedMachineId]);

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
      setConnectionError(null);

      if (machines.length > 0) {
        const telemResults = await Promise.all(
          machines.map(async (m) => {
            try {
              const pt = await api.getLatestTelemetry(m.machine_id);
              return { id: m.machine_id, pt };
            } catch {
              return { id: m.machine_id, pt: null };
            }
          })
        );
        const newMap: Record<string, TelemetryPoint> = {};
        telemResults.forEach((r) => { if (r.pt) newMap[r.id] = r.pt; });
        setTelemetryMap((prev) => ({ ...prev, ...newMap }));
      }

      if (selectedMachineId) {
        const history = await api.getTelemetryHistory(selectedMachineId, 50).catch(() => []);
        setTelemetryHistory(history);
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [machines, selectedMachineId]);

  useEffect(() => { loadInitialData(); }, [loadInitialData]);

  useEffect(() => {
    pollLiveData();
    const interval = setInterval(pollLiveData, 2000);
    return () => clearInterval(interval);
  }, [pollLiveData]);

  const handleAcknowledgeAlert = async (alertId: string) => {
    try { await api.acknowledgeAlert(alertId, 'ControlRoom_Op'); pollLiveData(); } catch {}
  };

  const handleResolveAlert = async (alertId: string) => {
    try { await api.resolveAlert(alertId); pollLiveData(); } catch {}
  };

  const selectedMachine = machines.find((m) => m.machine_id === selectedMachineId) || machines[0];

  // Initial loading skeleton
  if (isInitialLoad) {
    return (
      <div className="min-h-screen bg-[#05070f] bg-grid flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-2 border-sky-500/30 border-t-sky-400 rounded-full animate-spin mx-auto" />
          <p className="text-slate-400 text-sm font-mono">Connecting to ForgePulse backend…</p>
          <p className="text-slate-600 text-xs">Free tier instance may take 30–60s on cold start</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05070f] bg-grid text-slate-100 flex flex-col font-sans">
      <Header
        onRefresh={pollLiveData}
        isRefreshing={isRefreshing}
        onOpenFaultInjector={() => setIsFaultModalOpen(true)}
        health={systemHealth}
      />

      <DiagnosticsBar health={systemHealth} />

      {/* Connection Error Banner */}
      {connectionError && (
        <div className="bg-amber-500/10 border-b border-amber-500/20 px-6 py-2.5 text-xs text-amber-300 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse shrink-0" />
          {connectionError}
        </div>
      )}

      <main className="flex-1 max-w-screen-2xl w-full mx-auto px-6 py-6 space-y-6">
        {/* KPI Banner */}
        <FleetOverview summary={plantSummary} />

        {/* Section Label */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-500">
              Shop Floor Digital Twins &amp; Fleet Status
            </h2>
            <span className="text-[10px] font-mono text-slate-700">— click card to inspect live telemetry</span>
          </div>
          <span className="text-[10px] font-mono text-slate-700">{machines.length} machines monitored</span>
        </div>

        {/* Machine Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {machines.map((machine) => (
            <MachineCard
              key={machine.machine_id}
              machine={machine}
              latestTelemetry={telemetryMap[machine.machine_id]}
              isSelected={selectedMachineId === machine.machine_id}
              onSelect={setSelectedMachineId}
              onOpenTwin={setActiveTwinId}
            />
          ))}
        </div>

        {/* Telemetry Charts + Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2">
            {selectedMachine && (
              <LiveTelemetryChart machine={selectedMachine} history={telemetryHistory} />
            )}
          </div>
          <div className="lg:col-span-1 min-h-[400px]">
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
