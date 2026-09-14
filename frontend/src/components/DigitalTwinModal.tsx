import React, { useEffect, useState } from 'react';
import { DigitalTwin } from '../types';
import { api } from '../api/client';
import { X, Cpu, Wrench, Clock, Activity, Flame, Zap, Gauge, Radio } from 'lucide-react';

interface DigitalTwinModalProps {
  machineId: string | null;
  onClose: () => void;
}

/** Full SVG Ring Gauge for health score */
const HealthRing: React.FC<{ value: number }> = ({ value }) => {
  const size = 120;
  const r = 50;
  const cx = size / 2;
  const cy = size / 2;
  const c = 2 * Math.PI * r;
  const filled = (value / 100) * c;
  const color = value >= 85 ? '#34d399' : value >= 60 ? '#fbbf24' : '#fb7185';
  const label = value >= 85 ? 'HEALTHY' : value >= 60 ? 'WARNING' : 'CRITICAL';
  const labelColor = value >= 85 ? '#34d399' : value >= 60 ? '#fbbf24' : '#fb7185';

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {/* Outer glow */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth={10} />
        <circle
          cx={cx} cy={cy} r={r} fill="none"
          stroke={color} strokeWidth={10} strokeLinecap="round"
          strokeDasharray={`${filled} ${c - filled}`}
          style={{ filter: `drop-shadow(0 0 8px ${color}60)`, transition: 'stroke-dasharray 0.6s ease' }}
        />
        <text
          x={cx} y={cy}
          textAnchor="middle" dominantBaseline="central"
          style={{ transform: 'rotate(90deg)', transformOrigin: `${cx}px ${cy}px`, fontFamily: 'JetBrains Mono, monospace', fontSize: '22px', fontWeight: 800, fill: color }}
        >
          {value.toFixed(0)}%
        </text>
      </svg>
      <span className="text-[10px] font-mono font-bold tracking-widest" style={{ color: labelColor }}>{label}</span>
    </div>
  );
};

/** Penalty bar */
const PenaltyBar: React.FC<{ label: string; penalty: number; color: string }> = ({ label, penalty, color }) => (
  <div className="space-y-1">
    <div className="flex justify-between text-[11px]">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono font-semibold" style={{ color: penalty > 0 ? color : '#475569' }}>
        {penalty > 0 ? `-${penalty.toFixed(1)}` : '—'}
      </span>
    </div>
    <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${Math.min(100, penalty * 3.33)}%`, backgroundColor: penalty > 0 ? color : 'transparent' }}
      />
    </div>
  </div>
);

/** Production stat */
const Stat: React.FC<{ label: string; value: string; icon: React.ElementType; color: string }> = ({ label, value, icon: Icon, color }) => (
  <div className="bg-white/[0.025] border border-white/[0.05] rounded-xl p-3 text-center">
    <Icon className={`w-4 h-4 mx-auto mb-1.5 ${color}`} />
    <div className={`text-lg font-bold font-mono stat-value ${color}`}>{value}</div>
    <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
  </div>
);

export const DigitalTwinModal: React.FC<DigitalTwinModalProps> = ({ machineId, onClose }) => {
  const [twin, setTwin] = useState<DigitalTwin | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!machineId) return;
    const fetch = async () => {
      try {
        setLoading(true);
        const data = await api.getDigitalTwin(machineId);
        setTwin(data);
        setError(null);
      } catch (err: any) {
        setError(err.message ?? 'Failed to load Digital Twin');
      } finally {
        setLoading(false);
      }
    };
    fetch();
    const interval = setInterval(fetch, 3000);
    return () => clearInterval(interval);
  }, [machineId]);

  if (!machineId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
      <div className="bg-[#0d1117] border border-white/[0.08] rounded-2xl w-full max-w-4xl shadow-2xl shadow-black/60 my-8 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] bg-sky-500/[0.03]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sky-500/10 border border-sky-500/20">
              <Cpu className="w-4 h-4 text-sky-400" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-base font-bold text-white font-mono">
                  {twin?.identity.machine_id ?? machineId}
                </h2>
                {twin && (
                  <>
                    <span className="text-[10px] px-2 py-0.5 rounded-md bg-slate-800/80 text-slate-400 border border-slate-700/50 font-mono">
                      {twin.identity.machine_type}
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${
                      twin.current_status === 'RUNNING'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-slate-800/80 text-slate-400 border border-slate-700/50'
                    }`}>
                      {twin.current_status}
                    </span>
                    <div className="flex items-center gap-1 text-[10px] text-slate-500">
                      <Radio className="w-3 h-3 text-sky-500/60 animate-pulse" />
                      <span>Live · 3s refresh</span>
                    </div>
                  </>
                )}
              </div>
              {twin && (
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {twin.identity.machine_name} &nbsp;·&nbsp; {twin.identity.manufacturer} ({twin.identity.model})
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-500 hover:text-white hover:bg-white/[0.06] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {loading && !twin ? (
            <div className="flex flex-col items-center gap-3 py-20 text-slate-500">
              <div className="w-8 h-8 border-2 border-sky-500/40 border-t-sky-400 rounded-full animate-spin" />
              <span className="text-sm">Loading Digital Twin…</span>
            </div>
          ) : error ? (
            <div className="text-center py-20 text-rose-400 text-sm">{error}</div>
          ) : twin ? (
            <div className="space-y-6">
              {/* Top: Health Ring + Penalty Breakdown + Maintenance */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Health Ring */}
                <div className="md:col-span-1 bg-white/[0.025] border border-white/[0.05] rounded-2xl p-5 flex flex-col items-center gap-4">
                  <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest self-start">Health Score</h3>
                  <HealthRing value={twin.health.overall_health} />
                  <div className="text-center text-[10px] font-mono text-slate-500 px-2 py-1.5 bg-slate-900/60 rounded-lg border border-white/[0.04] w-full text-center leading-relaxed">
                    {twin.health.formula_explanation}
                  </div>
                </div>

                {/* Penalty Breakdown */}
                <div className="bg-white/[0.025] border border-white/[0.05] rounded-2xl p-5 space-y-3">
                  <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Penalty Breakdown</h3>
                  <div className="flex justify-between text-[11px] pb-2 border-b border-white/[0.04]">
                    <span className="text-slate-400">Base Score</span>
                    <span className="font-mono text-white">100.0</span>
                  </div>
                  <PenaltyBar label="Temperature Penalty" penalty={twin.health.temperature_penalty} color="#f59e0b" />
                  <PenaltyBar label="Vibration Penalty"   penalty={twin.health.vibration_penalty}   color="#38bdf8" />
                  <PenaltyBar label="Pressure Penalty"    penalty={twin.health.pressure_penalty}    color="#a78bfa" />
                  <PenaltyBar label="Error / Downtime"    penalty={twin.health.error_penalty + twin.health.downtime_penalty} color="#fb7185" />
                  <div className="flex justify-between text-[12px] font-bold pt-2 border-t border-white/[0.04]">
                    <span className="text-slate-300">Final Score</span>
                    <span
                      className="font-mono"
                      style={{ color: twin.health.overall_health >= 85 ? '#34d399' : twin.health.overall_health >= 60 ? '#fbbf24' : '#fb7185' }}
                    >
                      {twin.health.overall_health.toFixed(1)}
                    </span>
                  </div>
                </div>

                {/* Predictive Maintenance */}
                <div className="bg-white/[0.025] border border-white/[0.05] rounded-2xl p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Maintenance Risk</h3>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${
                      twin.maintenance_prediction.risk_level === 'CRITICAL' ? 'bg-rose-500/15 text-rose-400' :
                      twin.maintenance_prediction.risk_level === 'HIGH'     ? 'bg-amber-500/15 text-amber-400' :
                      twin.maintenance_prediction.risk_level === 'MEDIUM'   ? 'bg-sky-500/15 text-sky-400' :
                                                                              'bg-emerald-500/15 text-emerald-400'
                    }`}>
                      {twin.maintenance_prediction.risk_level} · {twin.maintenance_prediction.risk_score}%
                    </span>
                  </div>

                  {twin.maintenance_prediction.signals.length > 0 ? (
                    <ul className="space-y-1">
                      {twin.maintenance_prediction.signals.map((s, i) => (
                        <li key={i} className="flex items-start gap-1.5 text-[11px] text-slate-300">
                          <span className="text-amber-400 mt-0.5 shrink-0">▸</span>
                          {s}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-[11px] text-slate-600 italic">No degradation signals detected.</p>
                  )}

                  <div className="bg-amber-500/[0.08] border border-amber-500/15 rounded-xl p-3 text-[11px] text-amber-200/80">
                    <span className="font-semibold text-amber-300 block mb-1">
                      <Wrench className="w-3 h-3 inline mr-1" />Recommendation
                    </span>
                    {twin.maintenance_prediction.recommendation}
                  </div>
                </div>
              </div>

              {/* Production Stats */}
              <div>
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Production Statistics</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <Stat label="Parts Produced" value={twin.production.total_parts.toLocaleString()} icon={Activity} color="text-sky-400" />
                  <Stat label="Operating Hours" value={`${twin.production.operating_hours.toFixed(1)}h`} icon={Clock} color="text-emerald-400" />
                  <Stat label="Downtime (min)" value={`${twin.production.downtime_minutes.toFixed(0)}m`} icon={Zap} color="text-rose-400" />
                  <Stat label="Run Duration" value={`${twin.production.current_run_duration_minutes.toFixed(0)}m`} icon={Gauge} color="text-violet-400" />
                </div>
              </div>

              {/* Design Envelope */}
              <div className="bg-white/[0.018] border border-white/[0.04] rounded-2xl p-4">
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Design Operating Envelope</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                  {[
                    { label: 'Rated Speed', value: `${twin.identity.rated_rpm ?? '—'} RPM`, icon: Gauge },
                    { label: 'Thermal Limit', value: `${twin.identity.temperature_limit} °C`, icon: Flame },
                    { label: 'Vibration Limit', value: `${twin.identity.vibration_limit} mm/s`, icon: Activity },
                    { label: 'Pressure Limit', value: `${twin.identity.pressure_limit} bar`, icon: Zap },
                  ].map(({ label, value, icon: Icon }) => (
                    <div key={label} className="space-y-1">
                      <div className="flex items-center gap-1 text-slate-500">
                        <Icon className="w-3 h-3" />
                        <span className="text-[10px]">{label}</span>
                      </div>
                      <div className="text-white font-bold">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
