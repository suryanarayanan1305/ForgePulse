import React from 'react';
import { Machine, TelemetryPoint } from '../types';
import { Activity, Gauge, Flame, Zap, Compass, CheckCircle, AlertTriangle, AlertOctagon, Power } from 'lucide-react';

interface MachineCardProps {
  machine: Machine;
  latestTelemetry?: TelemetryPoint;
  isSelected: boolean;
  onSelect: (machineId: string) => void;
  onOpenTwin: (machineId: string) => void;
}

export const MachineCard: React.FC<MachineCardProps> = ({
  machine,
  latestTelemetry,
  isSelected,
  onSelect,
  onOpenTwin,
}) => {
  const status = machine.current_status;
  const isRunning = status === 'RUNNING';
  const isFault = status === 'FAULT';
  const isWarning = status === 'MAINTENANCE';

  // Status color styles
  const statusBadge = isRunning
    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
    : isFault
    ? 'bg-rose-500/10 text-rose-400 border-rose-500/20 animate-pulse'
    : isWarning
    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
    : 'bg-slate-500/10 text-slate-400 border-slate-500/20';

  const temp = latestTelemetry?.temperature ?? 30.0;
  const vib = latestTelemetry?.vibration ?? 0.5;
  const rpm = latestTelemetry?.rpm ?? 0;
  const power = latestTelemetry?.power_consumption ?? 0;

  // Approximate health
  let healthScore = 95;
  if (temp > machine.temperature_limit) healthScore -= 30;
  if (vib > machine.vibration_limit) healthScore -= 35;
  if (isFault) healthScore -= 30;
  healthScore = Math.max(10, Math.min(100, healthScore));

  const healthColor =
    healthScore >= 85 ? 'text-emerald-400' : healthScore >= 60 ? 'text-amber-400' : 'text-rose-400';

  return (
    <div
      onClick={() => onSelect(machine.machine_id)}
      className={`rounded-xl bg-slate-900/90 border p-4 transition-all duration-200 cursor-pointer relative overflow-hidden flex flex-col justify-between ${
        isSelected
          ? 'border-sky-500 ring-1 ring-sky-500/50 shadow-lg shadow-sky-500/10'
          : 'border-slate-800 hover:border-slate-700'
      }`}
    >
      {/* Top Bar: Identity & Status */}
      <div>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-white text-base tracking-wide">
                {machine.machine_id}
              </span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                {machine.machine_type}
              </span>
            </div>
            <p className="text-xs text-slate-400 truncate max-w-[160px]">{machine.machine_name}</p>
          </div>

          <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${statusBadge}`}>
            {status}
          </span>
        </div>

        {/* Real-Time Metrics Grid */}
        <div className="grid grid-cols-2 gap-2 my-3">
          {/* Temperature */}
          <div className="bg-slate-950/60 rounded-lg p-2 border border-slate-800/80">
            <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
              <span className="flex items-center gap-1">
                <Flame className="w-3 h-3 text-amber-400" /> Temp
              </span>
              <span className="font-mono text-[10px] text-slate-500">max {machine.temperature_limit}°</span>
            </div>
            <div className="font-mono text-sm font-semibold text-white">
              {temp.toFixed(1)} <span className="text-xs font-normal text-slate-400">°C</span>
            </div>
          </div>

          {/* Vibration */}
          <div className="bg-slate-950/60 rounded-lg p-2 border border-slate-800/80">
            <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
              <span className="flex items-center gap-1">
                <Activity className="w-3 h-3 text-sky-400" /> Vib
              </span>
              <span className="font-mono text-[10px] text-slate-500">max {machine.vibration_limit}</span>
            </div>
            <div className="font-mono text-sm font-semibold text-white">
              {vib.toFixed(3)} <span className="text-xs font-normal text-slate-400">mm/s</span>
            </div>
          </div>

          {/* RPM */}
          <div className="bg-slate-950/60 rounded-lg p-2 border border-slate-800/80">
            <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
              <span className="flex items-center gap-1">
                <Compass className="w-3 h-3 text-purple-400" /> Speed
              </span>
            </div>
            <div className="font-mono text-sm font-semibold text-white">
              {rpm.toFixed(0)} <span className="text-xs font-normal text-slate-400">RPM</span>
            </div>
          </div>

          {/* Power */}
          <div className="bg-slate-950/60 rounded-lg p-2 border border-slate-800/80">
            <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
              <span className="flex items-center gap-1">
                <Zap className="w-3 h-3 text-emerald-400" /> Power
              </span>
            </div>
            <div className="font-mono text-sm font-semibold text-white">
              {power.toFixed(1)} <span className="text-xs font-normal text-slate-400">kW</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Bar: Health Score & Action */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between mt-1">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-slate-400">Health:</span>
          <span className={`font-mono text-sm font-bold ${healthColor}`}>{healthScore}%</span>
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onOpenTwin(machine.machine_id);
          }}
          className="text-xs font-medium text-sky-400 hover:text-sky-300 hover:underline flex items-center gap-1"
        >
          <span>Digital Twin &rarr;</span>
        </button>
      </div>
    </div>
  );
};
