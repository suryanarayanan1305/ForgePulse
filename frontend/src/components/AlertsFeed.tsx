import React from 'react';
import { Alert } from '../types';
import { AlertOctagon, AlertTriangle, Info, Check, ShieldCheck } from 'lucide-react';

interface AlertsFeedProps {
  alerts: Alert[];
  onAcknowledge: (alertId: string) => void;
  onResolve: (alertId: string) => void;
}

export const AlertsFeed: React.FC<AlertsFeedProps> = ({ alerts, onAcknowledge, onResolve }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <span>Operational Alerts</span>
            {alerts.length > 0 && (
              <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                {alerts.length} OPEN
              </span>
            )}
          </h2>
          <p className="text-xs text-slate-400">Multi-tier anomaly events & automated cooldown deduplication</p>
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center text-slate-500">
          <ShieldCheck className="w-10 h-10 text-emerald-500/60 mb-2" />
          <p className="text-sm font-medium text-slate-300">All Asset Metrics Nominal</p>
          <p className="text-xs text-slate-500">No active operational alerts or threshold violations detected.</p>
        </div>
      ) : (
        <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
          {alerts.map((alert) => {
            const isCritical = alert.severity === 'CRITICAL';
            const isWarning = alert.severity === 'WARNING';

            const badgeBg = isCritical
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              : isWarning
              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              : 'bg-sky-500/10 text-sky-400 border-sky-500/30';

            const Icon = isCritical ? AlertOctagon : isWarning ? AlertTriangle : Info;

            return (
              <div
                key={alert.alert_id}
                className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-slate-700 transition"
              >
                <div className="flex items-start gap-3">
                  <div className={`p-1.5 rounded-md border mt-0.5 ${badgeBg}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-xs text-white">{alert.machine_id}</span>
                      <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded border ${badgeBg}`}>
                        {alert.severity}
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-0.5">{alert.message}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center">
                  {alert.status === 'OPEN' ? (
                    <button
                      onClick={() => onAcknowledge(alert.alert_id)}
                      className="px-2.5 py-1 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1 transition"
                    >
                      <Check className="w-3 h-3 text-sky-400" />
                      <span>Ack</span>
                    </button>
                  ) : (
                    <span className="text-[11px] text-slate-400 font-mono">Ack'd by {alert.acknowledged_by}</span>
                  )}

                  <button
                    onClick={() => onResolve(alert.alert_id)}
                    className="px-2.5 py-1 rounded text-xs font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 transition"
                  >
                    <span>Resolve</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
