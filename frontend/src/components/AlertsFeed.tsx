import React from 'react';
import { Alert } from '../types';
import { AlertOctagon, AlertTriangle, Info, Check, ShieldCheck, X, Clock } from 'lucide-react';

interface AlertsFeedProps {
  alerts: Alert[];
  onAcknowledge: (alertId: string) => void;
  onResolve: (alertId: string) => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

export const AlertsFeed: React.FC<AlertsFeedProps> = ({ alerts, onAcknowledge, onResolve }) => {
  return (
    <div className="flex flex-col bg-white/[0.025] border border-white/[0.06] rounded-2xl overflow-hidden shadow-xl h-full">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/[0.05] shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            Operational Alerts
            {alerts.length > 0 && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/25 animate-pulse">
                {alerts.length} OPEN
              </span>
            )}
          </h2>
        </div>
        <p className="text-[11px] text-slate-500 mt-0.5">3-tier anomaly detection · 300s cooldown deduplication</p>
      </div>

      {/* Alert List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-3 py-3 space-y-2">
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="p-4 rounded-full bg-emerald-500/10 mb-3">
              <ShieldCheck className="w-8 h-8 text-emerald-500/70" />
            </div>
            <p className="text-sm font-semibold text-slate-300">All Systems Nominal</p>
            <p className="text-[11px] text-slate-600 mt-1 max-w-[200px]">
              No active alerts. All sensor thresholds within safe operating limits.
            </p>
          </div>
        ) : (
          alerts.map((alert) => {
            const isCritical = alert.severity === 'CRITICAL';
            const isWarning = alert.severity === 'WARNING';

            const borderColor = isCritical ? 'border-rose-500/30' : isWarning ? 'border-amber-500/25' : 'border-sky-500/20';
            const accentBar = isCritical ? 'bg-rose-400' : isWarning ? 'bg-amber-400' : 'bg-sky-400';
            const shimmer = isCritical ? 'critical-shimmer' : '';
            const Icon = isCritical ? AlertOctagon : isWarning ? AlertTriangle : Info;
            const iconColor = isCritical ? 'text-rose-400' : isWarning ? 'text-amber-400' : 'text-sky-400';

            return (
              <div
                key={alert.alert_id}
                className={`relative rounded-xl border ${borderColor} ${shimmer} overflow-hidden p-3 transition-all duration-200 hover:border-opacity-50`}
                style={{ backgroundColor: 'rgba(255,255,255,0.02)' }}
              >
                {/* Left accent bar */}
                <div className={`absolute left-0 top-0 bottom-0 w-0.5 ${accentBar}`} />

                <div className="pl-2 space-y-2">
                  {/* Top Row */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 flex-1 min-w-0">
                      <Icon className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${iconColor}`} />
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-1.5 mb-0.5">
                          <span className="font-mono font-bold text-[11px] text-white">{alert.machine_id}</span>
                          <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full ${
                            isCritical ? 'bg-rose-500/15 text-rose-400' : isWarning ? 'bg-amber-500/15 text-amber-400' : 'bg-sky-500/15 text-sky-400'
                          }`}>
                            {alert.severity}
                          </span>
                          <span className="text-[9px] text-slate-600 font-mono flex items-center gap-0.5">
                            <Clock className="w-2.5 h-2.5" />{timeAgo(alert.timestamp)}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-300 leading-snug">{alert.message}</p>
                        {alert.observed_value !== null && alert.threshold_value !== null && (
                          <p className="text-[10px] text-slate-600 mt-0.5 font-mono">
                            Observed: <span className={iconColor}>{alert.observed_value?.toFixed(2)}</span>
                            {' '}/ Limit: {alert.threshold_value?.toFixed(2)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Action Row */}
                  <div className="flex items-center gap-1.5 justify-end">
                    {alert.status === 'OPEN' ? (
                      <button
                        onClick={() => onAcknowledge(alert.alert_id)}
                        className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 transition"
                        title="Acknowledge this alert"
                      >
                        <Check className="w-3 h-3 text-sky-400" />
                        Acknowledge
                      </button>
                    ) : (
                      <span className="text-[10px] text-slate-600 font-mono">
                        Ack: {alert.acknowledged_by}
                      </span>
                    )}
                    <button
                      onClick={() => onResolve(alert.alert_id)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 transition"
                      title="Mark as resolved"
                    >
                      <X className="w-3 h-3" />
                      Resolve
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
