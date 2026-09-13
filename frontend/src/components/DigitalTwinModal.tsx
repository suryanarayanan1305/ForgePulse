import React, { useEffect, useState } from 'react';
import { DigitalTwin } from '../types';
import { api } from '../api/client';
import { X, Cpu, Heart, AlertTriangle, ShieldCheck, Wrench, Clock, Activity, Flame, Zap, Gauge } from 'lucide-react';

interface DigitalTwinModalProps {
  machineId: string | null;
  onClose: () => void;
}

export const DigitalTwinModal: React.FC<DigitalTwinModalProps> = ({ machineId, onClose }) => {
  const [twin, setTwin] = useState<DigitalTwin | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!machineId) return;

    const fetchTwin = async () => {
      try {
        setLoading(true);
        const data = await api.getDigitalTwin(machineId);
        setTwin(data);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to load Digital Twin');
      } finally {
        setLoading(false);
      }
    };

    fetchTwin();
    const interval = setInterval(fetchTwin, 3000);
    return () => clearInterval(interval);
  }, [machineId]);

  if (!machineId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {loading && !twin ? (
          <div className="py-20 text-center text-slate-400">Loading Digital Twin metadata...</div>
        ) : error ? (
          <div className="py-20 text-center text-rose-400">{error}</div>
        ) : twin ? (
          <div>
            {/* Header */}
            <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
              <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400">
                <Cpu className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-bold text-white font-mono">{twin.identity.machine_id}</h2>
                  <span className="text-xs px-2 py-0.5 rounded-md font-mono bg-slate-800 text-slate-300 border border-slate-700">
                    {twin.identity.machine_type}
                  </span>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-semibold ${
                      twin.current_status === 'RUNNING'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}
                  >
                    {twin.current_status}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  {twin.identity.machine_name} • {twin.identity.manufacturer} ({twin.identity.model})
                </p>
              </div>
            </div>

            {/* Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 my-6">
              {/* 1. Transparent Machine Health Breakdown */}
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800/80">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Heart className="w-4 h-4 text-rose-400" />
                    <span>Transparent Health Score Engine</span>
                  </h3>
                  <span className="text-lg font-bold font-mono text-emerald-400">
                    {twin.health.overall_health.toFixed(1)}%
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between text-slate-400">
                    <span>Base Score:</span>
                    <span className="font-mono text-white">100.0</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Temperature Penalty:</span>
                    <span className="font-mono text-amber-400">-{twin.health.temperature_penalty.toFixed(1)}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Vibration Penalty:</span>
                    <span className="font-mono text-sky-400">-{twin.health.vibration_penalty.toFixed(1)}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Pressure Penalty:</span>
                    <span className="font-mono text-purple-400">-{twin.health.pressure_penalty.toFixed(1)}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Error Code / Status Penalty:</span>
                    <span className="font-mono text-rose-400">
                      -{(twin.health.error_penalty + twin.health.downtime_penalty).toFixed(1)}
                    </span>
                  </div>

                  <div className="pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 bg-slate-900/50 p-2 rounded">
                    {twin.health.formula_explanation}
                  </div>
                </div>
              </div>

              {/* 2. Predictive Maintenance Risk */}
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800/80">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-amber-400" />
                    <span>Predictive Maintenance Risk</span>
                  </h3>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded font-mono font-bold ${
                      twin.maintenance_prediction.risk_level === 'CRITICAL'
                        ? 'bg-rose-500/20 text-rose-400'
                        : twin.maintenance_prediction.risk_level === 'HIGH'
                        ? 'bg-amber-500/20 text-amber-400'
                        : 'bg-emerald-500/20 text-emerald-400'
                    }`}
                  >
                    {twin.maintenance_prediction.risk_level} ({twin.maintenance_prediction.risk_score}%)
                  </span>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <span className="text-slate-400 font-medium">Risk Signals:</span>
                    {twin.maintenance_prediction.signals.length === 0 ? (
                      <p className="text-slate-500 italic mt-1">No degradation signals detected.</p>
                    ) : (
                      <ul className="list-disc list-inside text-slate-300 mt-1 space-y-0.5">
                        {twin.maintenance_prediction.signals.map((sig, idx) => (
                          <li key={idx}>{sig}</li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5 text-amber-300">
                    <span className="font-semibold block mb-0.5">Recommendation:</span>
                    {twin.maintenance_prediction.recommendation}
                  </div>

                  <p className="text-[10px] text-slate-500 italic">
                    {twin.maintenance_prediction.disclaimer}
                  </p>
                </div>
              </div>
            </div>

            {/* Design Envelope Specs */}
            <div className="bg-slate-950/50 border border-slate-800/80 rounded-xl p-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Design Operating Envelope & Limits
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                <div>
                  <span className="text-slate-500 block">Rated Speed</span>
                  <span className="text-white font-bold">{twin.identity.rated_rpm ?? 'N/A'} RPM</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Thermal Limit</span>
                  <span className="text-white font-bold">{twin.identity.temperature_limit} °C</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Vibration Limit</span>
                  <span className="text-white font-bold">{twin.identity.vibration_limit} mm/s</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Pressure Limit</span>
                  <span className="text-white font-bold">{twin.identity.pressure_limit} bar</span>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
