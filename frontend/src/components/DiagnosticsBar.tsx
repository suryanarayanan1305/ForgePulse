import React from 'react';
import { Database, Activity, Wifi, Cpu, CheckCircle2, AlertCircle, TrendingUp } from 'lucide-react';
import { SystemHealth } from '../types';

interface DiagnosticsBarProps {
  health: SystemHealth | null;
}

export const DiagnosticsBar: React.FC<DiagnosticsBarProps> = ({ health }) => {
  const isHealthy = health?.status === 'HEALTHY';
  const isDegraded = health?.status === 'DEGRADED';
  const messagesReceived = health?.components.mqtt_broker.messages_received ?? 0;

  return (
    <div
      className={`border-b px-6 py-2 transition-colors duration-300 ${
        isHealthy
          ? 'bg-emerald-500/[0.04] border-emerald-500/10'
          : isDegraded
          ? 'bg-amber-500/[0.04] border-amber-500/10'
          : 'bg-rose-500/[0.04] border-rose-500/10'
      }`}
    >
      <div className="max-w-screen-2xl mx-auto flex flex-wrap items-center justify-between gap-3 text-[11px]">
        {/* Overall Status */}
        <div className="flex items-center gap-2">
          {isHealthy ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <AlertCircle className={`w-3.5 h-3.5 ${isDegraded ? 'text-amber-400' : 'text-rose-400'}`} />
          )}
          <span className="font-semibold text-slate-400 uppercase tracking-widest text-[10px]">System</span>
          <span
            className={`font-mono font-bold ${
              isHealthy ? 'text-emerald-400' : isDegraded ? 'text-amber-400' : 'text-rose-400'
            }`}
          >
            {health?.status ?? 'INITIALIZING'}
          </span>
        </div>

        {/* Component Status Row */}
        <div className="flex flex-wrap items-center gap-4">
          {/* Database */}
          <div className="flex items-center gap-1.5">
            <Database className="w-3 h-3 text-slate-500" />
            <span className="text-slate-500">SQLite</span>
            <span
              className={`font-mono font-semibold ${
                health?.components.database.status === 'CONNECTED' ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {health?.components.database.status === 'CONNECTED'
                ? `${(health?.components.database.latency_ms ?? 0).toFixed(1)}ms`
                : 'OFFLINE'}
            </span>
          </div>

          <span className="text-slate-800">|</span>

          {/* MQTT */}
          <div className="flex items-center gap-1.5">
            <Wifi className="w-3 h-3 text-slate-500" />
            <span className="text-slate-500">MQTT</span>
            <span
              className={`font-mono font-semibold ${
                health?.components.mqtt_broker.status === 'CONNECTED' ? 'text-emerald-400' : 'text-amber-400'
              }`}
            >
              {health?.components.mqtt_broker.status === 'CONNECTED' ? 'CONNECTED' : 'HTTP-FALLBACK'}
            </span>
          </div>

          <span className="text-slate-800">|</span>

          {/* Telemetry Stream */}
          <div className="flex items-center gap-1.5">
            <Activity className="w-3 h-3 text-slate-500" />
            <span className="text-slate-500">Stream</span>
            <span
              className={`font-mono font-semibold ${
                health?.components.telemetry_stream.status === 'RECEIVING' ? 'text-emerald-400' : 'text-amber-400'
              }`}
            >
              {health?.components.telemetry_stream.status ?? 'IDLE'}
            </span>
          </div>

          <span className="text-slate-800">|</span>

          {/* Ingested count */}
          <div className="flex items-center gap-1.5">
            <TrendingUp className="w-3 h-3 text-slate-500" />
            <span className="text-slate-500">Ingested</span>
            <span className="font-mono font-semibold text-sky-400">{messagesReceived.toLocaleString()} msgs</span>
          </div>

          <span className="text-slate-800">|</span>

          {/* Analytics */}
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3 h-3 text-slate-500" />
            <span className="text-slate-500">ML Engine</span>
            <span
              className={`font-mono font-semibold ${
                health?.components.analytics_engine.status === 'READY' ? 'text-emerald-400' : 'text-amber-400'
              }`}
            >
              {health?.components.analytics_engine.status ?? 'INITIALIZING'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
