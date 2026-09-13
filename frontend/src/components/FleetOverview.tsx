import React from 'react';
import { PlantSummary } from '../types';
import { Layers, PlayCircle, AlertTriangle, AlertOctagon, Heart, Percent, Box } from 'lucide-react';

interface FleetOverviewProps {
  summary: PlantSummary | null;
}

export const FleetOverview: React.FC<FleetOverviewProps> = ({ summary }) => {
  if (!summary) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6 animate-pulse">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="h-24 bg-slate-900/60 rounded-xl border border-slate-800" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: 'Total Assets',
      value: summary.total_machines,
      icon: Layers,
      color: 'text-sky-400',
      bg: 'bg-sky-500/10',
      border: 'border-sky-500/20',
    },
    {
      label: 'Running',
      value: summary.running_machines,
      icon: PlayCircle,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
    },
    {
      label: 'Stopped / Idle',
      value: summary.stopped_machines,
      icon: Layers,
      color: 'text-slate-400',
      bg: 'bg-slate-500/10',
      border: 'border-slate-500/20',
    },
    {
      label: 'Warning / Faults',
      value: summary.fault_machines + summary.maintenance_machines,
      icon: AlertTriangle,
      color: summary.fault_machines > 0 ? 'text-rose-400' : 'text-amber-400',
      bg: summary.fault_machines > 0 ? 'bg-rose-500/10' : 'bg-amber-500/10',
      border: summary.fault_machines > 0 ? 'border-rose-500/20' : 'border-amber-500/20',
    },
    {
      label: 'Active Alerts',
      value: summary.active_alerts_count,
      icon: AlertOctagon,
      color: summary.active_alerts_count > 0 ? 'text-rose-400' : 'text-slate-400',
      bg: summary.active_alerts_count > 0 ? 'bg-rose-500/10' : 'bg-slate-500/10',
      border: summary.active_alerts_count > 0 ? 'border-rose-500/20' : 'border-slate-500/20',
    },
    {
      label: 'Average Health',
      value: `${summary.average_plant_health.toFixed(1)}%`,
      icon: Heart,
      color: summary.average_plant_health > 80 ? 'text-emerald-400' : 'text-amber-400',
      bg: summary.average_plant_health > 80 ? 'bg-emerald-500/10' : 'bg-amber-500/10',
      border: summary.average_plant_health > 80 ? 'border-emerald-500/20' : 'border-amber-500/20',
    },
    {
      label: 'Plant OEE',
      value: `${summary.plant_oee.toFixed(1)}%`,
      icon: Percent,
      color: summary.plant_oee > 75 ? 'text-sky-400' : 'text-amber-400',
      bg: summary.plant_oee > 75 ? 'bg-sky-500/10' : 'bg-amber-500/10',
      border: summary.plant_oee > 75 ? 'border-sky-500/20' : 'border-amber-500/20',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`p-3.5 rounded-xl bg-slate-900/80 border ${card.border} flex flex-col justify-between hover:border-slate-700 transition duration-150`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-medium text-slate-400 truncate">{card.label}</span>
              <div className={`p-1.5 rounded-lg ${card.bg}`}>
                <Icon className={`w-3.5 h-3.5 ${card.color}`} />
              </div>
            </div>
            <div className={`text-xl font-bold font-mono ${card.color}`}>{card.value}</div>
          </div>
        );
      })}
    </div>
  );
};
