import React, { useState, useEffect } from 'react';
import { FaultScenario, Machine } from '../types';
import { api } from '../api/client';
import { X, ShieldAlert, Zap, Flame, Activity, AlertOctagon, PowerOff, CheckCircle2 } from 'lucide-react';

interface FaultInjectorModalProps {
  isOpen: boolean;
  machines: Machine[];
  onClose: () => void;
  onFaultInjected?: () => void;
}

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
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (machines.length > 0 && !selectedMachine) {
      setSelectedMachine(machines[0].machine_id);
    }
  }, [machines, selectedMachine]);

  useEffect(() => {
    if (!isOpen) return;
    const fetchScenarios = async () => {
      try {
        const list = await api.getFaultScenarios();
        setScenarios(list);
        if (list.length > 0 && !selectedFault) {
          setSelectedFault(list[0].fault_name);
        }
      } catch (err) {
        console.error('Failed to load scenarios', err);
      }
    };
    fetchScenarios();
  }, [isOpen, selectedFault]);

  if (!isOpen) return null;

  const handleInject = async () => {
    if (!selectedMachine || !selectedFault) return;
    try {
      setInjecting(true);
      setFeedback(null);
      const res = await api.injectFault(selectedMachine, selectedFault);
      setFeedback(`Injected ${selectedFault} on ${selectedMachine}! Sensor metrics will alter in 1-2s.`);
      if (onFaultInjected) onFaultInjected();
    } catch (err: any) {
      setFeedback(`Injection failed: ${err.message}`);
    } finally {
      setInjecting(false);
    }
  };

  const handleClear = async () => {
    if (!selectedMachine) return;
    try {
      setInjecting(true);
      await api.clearFault(selectedMachine);
      setFeedback(`Cleared faults on ${selectedMachine}. Machine returning to nominal baseline.`);
      if (onFaultInjected) onFaultInjected();
    } catch (err: any) {
      setFeedback(`Clear failed: ${err.message}`);
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl shadow-2xl p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Live Fault Injection Console</h2>
            <p className="text-xs text-slate-400">
              Demonstrate closed-loop anomaly detection, alerting & health penalty pipeline
            </p>
          </div>
        </div>

        <div className="my-5 space-y-4">
          {/* Target Machine Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Target Machine:
            </label>
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
              {machines.map((m) => (
                <button
                  key={m.machine_id}
                  onClick={() => setSelectedMachine(m.machine_id)}
                  className={`p-2.5 rounded-lg border text-xs font-mono font-bold transition text-center ${
                    selectedMachine === m.machine_id
                      ? 'bg-sky-500/20 border-sky-500 text-sky-300 ring-1 ring-sky-500/50'
                      : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  {m.machine_id}
                </button>
              ))}
            </div>
          </div>

          {/* Fault Scenario Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Failure Scenario:
            </label>
            <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
              {scenarios.map((sc) => (
                <div
                  key={sc.fault_name}
                  onClick={() => setSelectedFault(sc.fault_name)}
                  className={`p-3 rounded-xl border cursor-pointer transition ${
                    selectedFault === sc.fault_name
                      ? 'bg-amber-500/15 border-amber-500/80 text-white ring-1 ring-amber-500/30'
                      : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs text-amber-400 font-mono">{sc.display_name}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      Intensity: {(sc.intensity * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{sc.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Status Feedback */}
          {feedback && (
            <div className="p-3 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0" />
              <span>{feedback}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-800">
            <button
              onClick={handleClear}
              disabled={injecting}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              Clear Faults (Reset)
            </button>

            <button
              onClick={handleInject}
              disabled={injecting || !selectedMachine || !selectedFault}
              className="px-5 py-2 rounded-lg text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 font-mono transition shadow-lg shadow-amber-500/20"
            >
              {injecting ? 'Injecting...' : 'TRIGGER INJECTION NOW'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
