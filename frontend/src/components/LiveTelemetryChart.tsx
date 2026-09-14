import React, { useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Scatter,
  ComposedChart,
} from 'recharts';
import { TelemetryPoint, Machine } from '../types';
import { Flame, Activity, Gauge, Zap, Radio } from 'lucide-react';

interface LiveTelemetryChartProps {
  machine: Machine;
  history: TelemetryPoint[];
}

type Tab = 'temperature' | 'vibration' | 'rpm' | 'power';

const TABS: { key: Tab; label: string; unit: string; color: string; gradient: string; icon: React.ElementType }[] = [
  { key: 'temperature', label: 'Temperature', unit: '°C', color: '#f59e0b', gradient: 'temperatureGrad', icon: Flame },
  { key: 'vibration',   label: 'Vibration',   unit: 'mm/s', color: '#38bdf8', gradient: 'vibrationGrad',   icon: Activity },
  { key: 'rpm',         label: 'Speed',        unit: 'RPM', color: '#a78bfa', gradient: 'rpmGrad',         icon: Gauge },
  { key: 'power',       label: 'Power',        unit: 'kW',  color: '#34d399', gradient: 'powerGrad',       icon: Zap },
];

const LIMITS: Record<Tab, (m: Machine) => number> = {
  temperature: (m) => m.temperature_limit,
  vibration:   (m) => m.vibration_limit,
  rpm:         (m) => m.rated_rpm ?? 8000,
  power:       (m) => m.power_limit ?? 22,
};

const CustomTooltip = ({ active, payload, label, unit, color }: any) => {
  if (!active || !payload?.length) return null;
  const v = payload[0]?.value;
  return (
    <div className="bg-[#0d1117] border border-white/[0.08] rounded-xl px-3 py-2 shadow-xl text-xs">
      <p className="text-slate-500 font-mono mb-1">{label}</p>
      <p className="font-mono font-bold" style={{ color }}>
        {typeof v === 'number' ? v.toFixed(2) : '—'} <span className="text-slate-400 font-normal">{unit}</span>
      </p>
    </div>
  );
};

export const LiveTelemetryChart: React.FC<LiveTelemetryChartProps> = ({ machine, history }) => {
  const [activeTab, setActiveTab] = useState<Tab>('temperature');

  const tab = TABS.find((t) => t.key === activeTab)!;
  const limit = LIMITS[activeTab](machine);

  const chartData = history.map((pt) => ({
    time: new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    value: pt[activeTab === 'power' ? 'power_consumption' : activeTab] as number | null,
    anomaly: pt.is_anomaly ? (pt[activeTab === 'power' ? 'power_consumption' : activeTab] as number) : null,
  }));

  const hasData = chartData.some((d) => d.value !== null);

  return (
    <div className="bg-white/[0.025] border border-white/[0.06] rounded-2xl overflow-hidden shadow-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-4 border-b border-white/[0.05]">
        <div>
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-sky-400 animate-pulse" />
            Live Telemetry Stream
            <span className="font-mono text-sky-400">[{machine.machine_id}]</span>
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Real-time sensor data · 2s polling interval · Anomaly detection active
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 p-1 bg-slate-900/80 border border-white/[0.05] rounded-xl">
          {TABS.map((t) => {
            const Icon = t.icon;
            const isActive = activeTab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all duration-200 ${
                  isActive
                    ? 'text-white shadow-sm'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
                style={isActive ? { backgroundColor: `${t.color}22`, color: t.color } : {}}
              >
                <Icon className="w-3 h-3" />
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Chart */}
      <div className="px-5 py-4">
        <div className="flex items-center justify-between text-[11px] mb-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: tab.color }} />
            <span className="text-slate-400 font-medium">{tab.label}</span>
            <span className="font-mono text-slate-600">({tab.unit})</span>
          </div>
          <span className="text-slate-600 font-mono">
            Limit: <span className="text-rose-400">{limit} {tab.unit}</span>
          </span>
        </div>

        <div className="h-64 w-full">
          {!hasData ? (
            <div className="h-full flex items-center justify-center text-slate-600 text-sm">
              Waiting for telemetry data…
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id={tab.gradient} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={tab.color} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={tab.color} stopOpacity={0.02} />
                  </linearGradient>
                </defs>

                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />

                <XAxis
                  dataKey="time"
                  stroke="transparent"
                  tick={{ fill: '#475569', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  stroke="transparent"
                  tick={{ fill: '#475569', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
                  tickLine={false}
                  width={40}
                  unit={` ${tab.unit.slice(0, 2)}`}
                />

                <Tooltip content={<CustomTooltip unit={tab.unit} color={tab.color} />} />

                {/* Critical Limit Line */}
                <ReferenceLine
                  y={limit}
                  stroke="#ef4444"
                  strokeDasharray="5 4"
                  strokeWidth={1.5}
                  label={{ value: 'LIMIT', fill: '#ef4444', fontSize: 9, position: 'right', fontFamily: 'JetBrains Mono, monospace' }}
                />

                {/* Area */}
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={tab.color}
                  strokeWidth={2}
                  fill={`url(#${tab.gradient})`}
                  dot={false}
                  isAnimationActive={false}
                  activeDot={{ r: 3, fill: tab.color, strokeWidth: 0 }}
                />

                {/* Anomaly dots */}
                <Scatter
                  dataKey="anomaly"
                  fill="#fb7185"
                  r={4}
                  shape={(props: any) => {
                    const { cx, cy } = props;
                    if (!cy || !cx) return <g />;
                    return (
                      <circle
                        cx={cx}
                        cy={cy}
                        r={4}
                        fill="#fb7185"
                        stroke="#fda4af"
                        strokeWidth={1}
                        style={{ filter: 'drop-shadow(0 0 4px #fb7185)' }}
                      />
                    );
                  }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
};
