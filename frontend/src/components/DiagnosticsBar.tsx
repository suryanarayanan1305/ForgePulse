import React from 'react';
import { Database, Activity, Radio, Cpu, CheckCircle2, AlertCircle } from 'lucide-react';
import { SystemHealth } from '../types';

interface DiagnosticsBarProps {
  health: SystemHealth | null;
}

export const DiagnosticsBar: React.FC<DiagnosticsBarProps> = ({ health }) => {
  const dbStatus = health?.components.database.status === 'CONNECTED';
  const mqttStatus = health?.components.mqtt_broker.status === 'CONNECTED';
  const streamStatus = health?.components.telemetry_stream.status === 'RECEIVING';
  const apiStatus = health?.components.api.status === 'HEALTHY';

  return (
    <div className="bg-slate-900/60 border-y border-slate-800/80 px-6 py-2.5">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
            System Diagnostics:
          </span>
          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full font-mono font-medium ${
            health?.status === 'HEALTHY' 
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
          }`}>
            {health?.status === 'HEALTHY' ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
            {health?.status || 'INITIALIZING'}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-6">
          {/* MQTT */}
          <div className="flex items-center gap-2">
            <Radio className={`w-3.5 h-3.5 ${mqttStatus ? 'text-emerald-400' : 'text-rose-400'}`} />
            <span className="text-slate-400">MQTT Broker:</span>
            <span className={`font-mono font-medium ${mqttStatus ? 'text-emerald-400' : 'text-rose-400'}`}>
              {mqttStatus ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>

          {/* Database */}
          <div className="flex items-center gap-2">
            <Database className={`w-3.5 h-3.5 ${dbStatus ? 'text-emerald-400' : 'text-rose-400'}`} />
            <span className="text-slate-400">PostgreSQL:</span>
            <span className={`font-mono font-medium ${dbStatus ? 'text-emerald-400' : 'text-rose-400'}`}>
              {dbStatus ? `${health?.components.database.latency_ms ?? 5}ms` : 'OFFLINE'}
            </span>
          </div>

          {/* Telemetry Stream */}
          <div className="flex items-center gap-2">
            <Activity className={`w-3.5 h-3.5 ${streamStatus ? 'text-emerald-400' : 'text-amber-400'}`} />
            <span className="text-slate-400">Telemetry Stream:</span>
            <span className={`font-mono font-medium ${streamStatus ? 'text-emerald-400' : 'text-amber-400'}`}>
              {streamStatus ? 'ACTIVE' : 'IDLE'}
            </span>
          </div>

          {/* Messages count */}
          <div className="flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-slate-400">Ingested:</span>
            <span className="font-mono text-slate-200">
              {health?.components.mqtt_broker.messages_received ?? 0} msgs
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
