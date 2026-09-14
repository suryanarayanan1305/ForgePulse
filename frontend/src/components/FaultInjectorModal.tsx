import React, { useState, useEffect } from 'react';
import { FaultScenario, Machine } from '../types';
import { api } from '../api/client';
import { X, ShieldAlert, CheckCircle2, AlertTriangle, RotateCcw, Zap } from 'lucide-react';

interface FaultInjectorModalProps {
  isOpen: boolean;
  machines: Machine[];
  onClose: () => void;
  onFaultInjected?: () => void;
}

const FAULT_ICONS: Record<string, string> = {
  OVERHEATING: '🌡️',
  HIGH_VIBRATION: '〰️',
  PRESSURE_SPIKE: '🔺',
  MOTOR_OVERLOAD: '⚡',
  MACHINE_STOP: '⛔',
  BEARING_FAULT: '🔩',
};

export const FaultInjectorModal: React.FC<FaultInjectorModalProps> = ({
  isOpen,
  machines,
  onClose,
  onFaultInjected,
}) => {
  const [scenarios, setScenarios] = useState<FaultScenario[]>([]);
  const [selectedMachine, setSelectedMachine] = useState<string>('');
  const [selectedFault, setSelectedFault] = useState<string>('');
  const [injecting, setInjecting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    if (machines.length > 0 && !selectedMachine) {
      setSelectedMachine(machines[0].machine_id);
    }
  }, [machines, selectedMachine]);

  useEffect(() => {
    if (!isOpen) return;
    api.getFaultScenarios()
      .then((list) => {
        setScenarios(list);
        if (list.length > 0 && !selectedFault) setSelectedFault(list[0].fault_name);
      })
      .catch(console.error);
  }, [isOpen, selectedFault]);

  if (!isOpen) return null;

  const handleInject = async () => {
    if (!selectedMachine || !selectedFault) return;
    try {
      setInjecting(true);
      setFeedback(null);
      await api.injectFault(selectedMachine, selectedFault);
      setFeedback({
        type: 'success',
        message: `✓ ${selectedFault} injected on ${selectedMachine}. Sensor metrics will deviate within 2–4 seconds.`,
      });
      onFaultInjected?.();
    } catch (err: any) {
      setFeedback({ type: 'error', message: `Injection failed: ${err.message}` });
    } finally {
      setInjecting(false);
    }
  };

  const handleClear = async () => {
    if (!selectedMachine) return;
    try {
      setInjecting(true);
      await api.clearFault(selectedMachine);
      setFeedback({
        type: 'success',
        message: `✓ Faults cleared on ${selectedMachine}. Machine returning to nominal baseline.`,
      });
      onFaultInjected?.();
    } catch (err: any) {
      setFeedback({ type: 'error', message: `Clear failed: ${err.message}` });
    } finally {
      setInjecting(false);
    }
  };

  const selectedScenario = scenarios.find((s) => s.fault_name === selectedFault);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4">
      <div className="bg-[#0d1117] border border-white/[0.08] rounded-2xl w-full max-w-2xl shadow-2xl shadow-black/50 overflow-hidden">
        {/* Hazard Header */}
        <div className="relative px-6 py-5 border-b border-amber-500/15 bg-amber-500/[0.04] overflow-hidden">
          {/* Hazard stripe decoration */}
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage: 'repeating-linear-gradient(-45deg, #f59e0b 0, #f59e0b 10px, transparent 10px, transparent 20px)',
            }}
          />
          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-amber-500/15 border border-amber-500/20">
                <ShieldAlert className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Live Fault Injection Console</h2>
                <p className="text-[11px] text-amber-500/70 mt-0.5">
                  Triggers deterministic failure scenarios on the physics simulation engine
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.06] transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Machine Selection */}
          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
              Target Machine
            </label>
            <div className="grid grid-cols-5 gap-2">
              {machines.map((m) => (
                <button
                  key={m.machine_id}
                  onClick={() => setSelectedMachine(m.machine_id)}
                  className={`p-2 rounded-xl border text-[11px] font-mono font-bold transition-all ${
                    selectedMachine === m.machine_id
                      ? 'bg-sky-500/15 border-sky-500/60 text-sky-300 ring-1 ring-sky-500/30'
                      : 'bg-white/[0.02] border-white/[0.06] text-slate-400 hover:border-sky-500/25 hover:text-slate-200'
                  }`}
                >
                  {m.machine_id}
                </button>
              ))}
            </div>
          </div>

          {/* Fault Scenario Selection */}
          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
              Failure Scenario
            </label>
            <div className="space-y-1.5 max-h-56 overflow-y-auto scrollbar-thin pr-1">
              {scenarios.map((sc) => {
                const isActive = selectedFault === sc.fault_name;
                const pct = Math.round(sc.intensity * 100);
                return (
                  <div
                    key={sc.fault_name}
                    onClick={() => setSelectedFault(sc.fault_name)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all ${
                      isActive
                        ? 'bg-amber-500/10 border-amber-500/40 ring-1 ring-amber-500/20'
                        : 'bg-white/[0.02] border-white/[0.05] hover:border-amber-500/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{FAULT_ICONS[sc.fault_name] ?? '⚠️'}</span>
                        <span className="font-semibold text-[12px] text-amber-300">{sc.display_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-slate-500">Intensity</span>
                        <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${pct > 75 ? 'bg-rose-400' : pct > 50 ? 'bg-amber-400' : 'bg-sky-400'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-slate-400">{pct}%</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-500 leading-snug">{sc.description}</p>
                    {isActive && sc.expected_alerts.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {sc.expected_alerts.map((a) => (
                          <span key={a} className="text-[9px] px-1.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono">
                            {a}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Feedback */}
          {feedback && (
            <div className={`flex items-start gap-2 p-3 rounded-xl border text-[11px] ${
              feedback.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
            }`}>
              <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <span>{feedback.message}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-white/[0.05]">
            <button
              onClick={handleClear}
              disabled={injecting}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-white/[0.04] hover:bg-white/[0.07] text-slate-300 border border-white/[0.07] transition disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Clear Faults (Reset)
            </button>

            <button
              onClick={handleInject}
              disabled={injecting || !selectedMachine || !selectedFault}
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-lg shadow-amber-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Zap className="w-3.5 h-3.5" />
              {injecting ? 'Injecting…' : 'Trigger Injection'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
