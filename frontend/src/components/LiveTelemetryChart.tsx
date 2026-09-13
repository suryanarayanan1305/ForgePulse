import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { TelemetryPoint, Machine } from '../types';
import { Activity, Flame } from 'lucide-react';

interface LiveTelemetryChartProps {
  machine: Machine;
  history: TelemetryPoint[];
}

export const LiveTelemetryChart: React.FC<LiveTelemetryChartProps> = ({ machine, history }) => {
  const chartData = history.map((pt) => ({
    time: new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    temperature: pt.temperature,
    vibration: pt.vibration,
    rpm: pt.rpm,
    is_anomaly: pt.is_anomaly,
  }));

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-800">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <span>Live Telemetry Stream</span>
            <span className="text-sky-400 font-mono">[{machine.machine_id}]</span>
          </h2>
          <p className="text-xs text-slate-400">
            Real-time sensor dynamics • Correlated thermal dissipation & vibration spectrum
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span className="text-slate-300">Temperature (°C)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
            <span className="text-slate-300">Vibration (mm/s)</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Temperature Chart */}
        <div>
          <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-2">
            <span className="flex items-center gap-1.5">
              <Flame className="w-3.5 h-3.5 text-amber-400" /> Spindle Temperature Trend
            </span>
            <span className="text-slate-500 font-mono text-[11px]">
              Limit: {machine.temperature_limit}°C
            </span>
          </div>
          <div className="h-52 w-full bg-slate-950/50 rounded-lg p-2 border border-slate-800/80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickMargin={5} />
                <YAxis
                  stroke="#64748b"
                  fontSize={10}
                  domain={[20, (dataMax: number) => Math.max(machine.temperature_limit + 10, Math.ceil(dataMax + 5))]}
                  unit="°"
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <ReferenceLine
                  y={machine.temperature_limit}
                  stroke="#ef4444"
                  strokeDasharray="4 4"
                  label={{ value: 'CRITICAL LIMIT', fill: '#ef4444', fontSize: 10, position: 'top' }}
                />
                <Line
                  type="monotone"
                  dataKey="temperature"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Vibration Chart */}
        <div>
          <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-2">
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-sky-400" /> Mechanical Vibration (RMS)
            </span>
            <span className="text-slate-500 font-mono text-[11px]">
              Limit: {machine.vibration_limit} mm/s
            </span>
          </div>
          <div className="h-52 w-full bg-slate-950/50 rounded-lg p-2 border border-slate-800/80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickMargin={5} />
                <YAxis
                  stroke="#64748b"
                  fontSize={10}
                  domain={[0, (dataMax: number) => Math.max(machine.vibration_limit + 3, Math.ceil(dataMax + 2))]}
                  unit="mm"
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <ReferenceLine
                  y={machine.vibration_limit}
                  stroke="#ef4444"
                  strokeDasharray="4 4"
                  label={{ value: 'VIB LIMIT', fill: '#ef4444', fontSize: 10, position: 'top' }}
                />
                <Line
                  type="monotone"
                  dataKey="vibration"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
