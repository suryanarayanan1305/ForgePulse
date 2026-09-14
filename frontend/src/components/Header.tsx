import React, { useState, useEffect } from 'react';
import { Activity, ShieldAlert, Cpu, RefreshCw, Radio, Database, Zap, Wifi } from 'lucide-react';
import { SystemHealth } from '../types';

interface HeaderProps {
  onRefresh: () => void;
  isRefreshing: boolean;
  onOpenFaultInjector: () => void;
  health?: SystemHealth | null;
}

export const Header: React.FC<HeaderProps> = ({ onRefresh, isRefreshing, onOpenFaultInjector, health }) => {
  const [timeStr, setTimeStr] = useState<string>('');
  const [blink, setBlink] = useState<boolean>(true);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const hh = now.getUTCHours().toString().padStart(2, '0');
      const mm = now.getUTCMinutes().toString().padStart(2, '0');
      const ss = now.getUTCSeconds().toString().padStart(2, '0');
      const day = now.toUTCString().split(' ').slice(0, 4).join(' ');
      setTimeStr(`${day} ${hh}:${mm}:${ss} UTC`);
      setBlink((b) => !b);
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const dbOk = health?.components.database.status === 'CONNECTED';
  const mqttOk = health?.components.mqtt_broker.status === 'CONNECTED';
  const streamOk = health?.components.telemetry_stream.status === 'RECEIVING';
  const dbLatency = health?.components.database.latency_ms;

  const StatusPill = ({
    ok,
    label,
    value,
    icon: Icon,
  }: {
    ok: boolean;
    label: string;
    value?: string;
    icon: React.ElementType;
  }) => (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900/80 border border-slate-800/80 text-[11px]">
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-emerald-400 led-pulse' : 'bg-rose-400 animate-pulse'}`} />
      <Icon className={`w-3 h-3 ${ok ? 'text-emerald-400' : 'text-rose-400'}`} />
      <span className="text-slate-500 font-medium">{label}</span>
      {value && <span className={`font-mono font-semibold ${ok ? 'text-emerald-400' : 'text-rose-400'}`}>{value}</span>}
    </div>
  );

  return (
    <header className="bg-[#080b14]/95 border-b border-white/[0.06] backdrop-blur-xl sticky top-0 z-40">
      <div className="max-w-screen-2xl mx-auto px-6 py-3 flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Brand Identity */}
        <div className="flex items-center gap-4">
          {/* Animated Logo Ring */}
          <div className="relative w-10 h-10 shrink-0">
            <div className="absolute inset-0 rounded-xl bg-gradient-to-tr from-sky-600 via-cyan-400 to-sky-300 opacity-20 blur-sm animate-pulse" />
            <div className="relative w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-700 to-cyan-400 flex items-center justify-center shadow-lg shadow-sky-500/30 border border-sky-400/20">
              <Cpu className="w-5 h-5 text-white" />
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg font-bold tracking-tight text-white leading-none">
                FORGE<span className="text-sky-400">PULSE</span>
              </h1>
              <span className="px-2 py-0.5 rounded-md text-[9px] font-bold tracking-widest bg-sky-500/10 text-sky-400 border border-sky-500/20 uppercase">
                IIoT · Digital Twin
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5 leading-none">
              PLANT-A &nbsp;·&nbsp; Chennai Advanced Manufacturing Facility
            </p>
          </div>
        </div>

        {/* Status Pills + Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* System status pills */}
          <div className="flex items-center gap-1.5 border-r border-slate-800 pr-3 mr-1">
            <StatusPill ok={dbOk} label="DB" value={dbOk && dbLatency ? `${dbLatency.toFixed(1)}ms` : undefined} icon={Database} />
            <StatusPill ok={mqttOk} label="MQTT" icon={Wifi} />
            <StatusPill ok={streamOk} label="Stream" icon={Activity} />
          </div>

          {/* UTC Clock */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800/80 text-xs font-mono text-slate-300">
            <Radio className="w-3 h-3 text-sky-400 animate-pulse shrink-0" />
            <span className="tabular-nums">{timeStr || '...'}</span>
          </div>

          {/* Inject Failure */}
          <button
            onClick={onOpenFaultInjector}
            className="group relative flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30 hover:bg-amber-500/20 hover:border-amber-400/60 transition-all duration-200 overflow-hidden"
          >
            <span className="absolute inset-0 bg-amber-400/5 opacity-0 group-hover:opacity-100 transition-opacity" />
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>Inject Failure</span>
          </button>

          {/* Sync */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900/80 hover:bg-slate-800/80 text-slate-300 border border-slate-800/80 hover:border-slate-700 transition-all duration-200"
            title="Force refresh all metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-sky-400' : 'text-slate-400'}`} />
            <span>Sync</span>
          </button>
        </div>
      </div>
    </header>
  );
};
