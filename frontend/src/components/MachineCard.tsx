import React from 'react';
import { Machine, TelemetryPoint } from '../types';
import { Flame, Activity, Gauge, Zap, Settings } from 'lucide-react';

interface MachineCardProps {
  machine: Machine;
  latestTelemetry?: TelemetryPoint;
  isSelected: boolean;
  onSelect: (machineId: string) => void;
  onOpenTwin: (machineId: string) => void;
}

/** SVG circular arc health gauge */
const HealthGauge: React.FC<{ value: number; size?: number }> = ({ value, size = 52 }) => {
  const r = (size - 8) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;
  const strokeDash = (value / 100) * circumference;
  const gap = circumference - strokeDash;

  const color =
    value >= 85 ? '#34d399' : value >= 60 ? '#fbbf24' : '#fb7185';
  const bgColor = 'rgba(255,255,255,0.04)';

  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      {/* Track */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={bgColor} strokeWidth={5} />
      {/* Arc */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={5}
        strokeLinecap="round"
        strokeDasharray={`${strokeDash} ${gap}`}
        style={{ filter: `drop-shadow(0 0 3px ${color}60)`, transition: 'stroke-dasharray 0.5s ease' }}
      />
      {/* Center text — rotate back */}
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        style={{ transform: 'rotate(90deg)', transformOrigin: `${cx}px ${cy}px`, fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', fontWeight: 700, fill: color }}
      >
        {value}%
      </text>
    </svg>
  );
};

/** Mini metric progress bar */
const MetricBar: React.FC<{
  icon: React.ElementType;
  label: string;
  value: number;
  max: number;
  unit: string;
  color: string;
  iconColor: string;
}> = ({ icon: Icon, label, value, max, unit, color, iconColor }) => {
  const pct = Math.min(100, (value / max) * 100);
  const isOver = value > max;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px]">
        <span className={`flex items-center gap-1 font-medium ${isOver ? 'text-rose-400' : 'text-slate-400'}`}>
          <Icon className={`w-2.5 h-2.5 ${isOver ? 'text-rose-400' : iconColor}`} />
          {label}
        </span>
        <span className={`font-mono font-semibold ${isOver ? 'text-rose-400' : 'text-white'}`}>
          {typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : '—'} <span className="text-slate-500 font-normal">{unit}</span>
        </span>
      </div>
      <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${isOver ? 'bg-rose-400' : color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

const MACHINE_TYPE_ICONS: Record<string, string> = {
  CNC: '⚙',
  PRESS: '🔩',
  MILL: '🔧',
  LATHE: '⚡',
};

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
  const isMaint = status === 'MAINTENANCE';

  const temp = latestTelemetry?.temperature ?? 30;
  const vib = latestTelemetry?.vibration ?? 0.5;
  const rpm = latestTelemetry?.rpm ?? 0;
  const power = latestTelemetry?.power_consumption ?? 0;
  const isAnomaly = latestTelemetry?.is_anomaly ?? false;

  // Health calculation (simplified frontend estimate)
  let health = 100;
  if (temp > machine.temperature_limit) health -= 30;
  else if (temp > machine.temperature_limit * 0.85) health -= 10;
  if (vib > machine.vibration_limit) health -= 35;
  else if (vib > machine.vibration_limit * 0.8) health -= 12;
  if (isFault) health -= 25;
  if (isMaint) health -= 10;
  health = Math.max(5, Math.min(100, health));

  // Card border/glow based on state
  const cardStyles = isSelected
    ? 'border-sky-500/60 ring-1 ring-sky-500/25 shadow-xl shadow-sky-500/10 bg-sky-500/[0.04]'
    : isFault
    ? 'border-rose-500/30 bg-rose-500/[0.02]'
    : isAnomaly
    ? 'border-amber-500/30 bg-amber-500/[0.02]'
    : 'border-white/[0.06] hover:border-sky-500/25 hover:bg-white/[0.035]';

  // LED dot color
  const ledColor = isRunning
    ? 'bg-emerald-400 shadow-emerald-400/50'
    : isFault
    ? 'bg-rose-400 shadow-rose-400/50'
    : isMaint
    ? 'bg-amber-400 shadow-amber-400/50'
    : 'bg-slate-600';

  const statusColor = isRunning
    ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    : isFault
    ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
    : isMaint
    ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
    : 'text-slate-400 bg-slate-800/60 border-slate-700/40';

  return (
    <div
      onClick={() => onSelect(machine.machine_id)}
      className={`relative rounded-2xl border p-4 transition-all duration-200 cursor-pointer flex flex-col gap-3 bg-white/[0.025] ${cardStyles}`}
    >
      {/* Anomaly indicator */}
      {isAnomaly && (
        <div className="absolute top-2 right-2">
          <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse">
            ANOMALY
          </span>
        </div>
      )}

      {/* Header: ID + Status LED + Type */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full shadow-md shrink-0 ${ledColor} ${isRunning ? 'led-pulse' : isFault ? 'animate-pulse' : ''}`}
            />
            <span className="font-mono font-bold text-white text-sm tracking-wide">{machine.machine_id}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-slate-800/80 text-slate-500 border border-slate-700/50 font-mono">
              {MACHINE_TYPE_ICONS[machine.machine_type] || ''} {machine.machine_type}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 truncate mt-0.5 pl-4">{machine.machine_name}</p>
        </div>

        {/* Health Gauge */}
        <HealthGauge value={health} size={52} />
      </div>

      {/* Status Badge */}
      <span className={`self-start text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold border ${statusColor}`}>
        {status}
      </span>

      {/* Metric Bars */}
      <div className="space-y-2.5">
        <MetricBar
          icon={Flame}
          label="Temperature"
          value={temp}
          max={machine.temperature_limit}
          unit="°C"
          color="bg-amber-400"
          iconColor="text-amber-400"
        />
        <MetricBar
          icon={Activity}
          label="Vibration"
          value={vib}
          max={machine.vibration_limit}
          unit="mm/s"
          color="bg-sky-400"
          iconColor="text-sky-400"
        />
        <MetricBar
          icon={Gauge}
          label="Speed"
          value={rpm}
          max={machine.rated_rpm ?? 8000}
          unit="RPM"
          color="bg-violet-400"
          iconColor="text-violet-400"
        />
        <MetricBar
          icon={Zap}
          label="Power"
          value={power}
          max={machine.power_limit ?? 22}
          unit="kW"
          color="bg-emerald-400"
          iconColor="text-emerald-400"
        />
      </div>

      {/* Footer: Digital Twin Link */}
      <div className="pt-2 border-t border-white/[0.05]">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onOpenTwin(machine.machine_id);
          }}
          className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-xl text-[11px] font-semibold text-sky-400 bg-sky-500/[0.08] hover:bg-sky-500/[0.16] border border-sky-500/15 hover:border-sky-500/30 transition-all duration-200"
        >
          <Settings className="w-3 h-3" />
          <span>Digital Twin</span>
          <span>→</span>
        </button>
      </div>
    </div>
  );
};
