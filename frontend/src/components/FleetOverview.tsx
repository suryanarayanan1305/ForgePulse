import React from 'react';
import { PlantSummary } from '../types';
import { Layers, PlayCircle, StopCircle, AlertTriangle, BellRing, Heart, BarChart3, Package } from 'lucide-react';

interface FleetOverviewProps {
  summary: PlantSummary | null;
}

interface KPICardProps {
  label: string;
  value: string | number;
  subLabel?: string;
  icon: React.ElementType;
  accent: string;       // Tailwind color class for the glow/accent
  iconBg: string;
  iconColor: string;
  borderColor: string;
  loading?: boolean;
}

const KPICard: React.FC<KPICardProps> = ({
  label, value, subLabel, icon: Icon, accent, iconBg, iconColor, borderColor, loading
}) => {
  if (loading) {
    return (
      <div className="rounded-2xl bg-white/[0.025] border border-white/[0.05] p-4 animate-pulse">
        <div className="h-3 w-16 bg-slate-800 rounded mb-3" />
        <div className="h-8 w-12 bg-slate-800 rounded" />
      </div>
    );
  }

  return (
    <div
      className={`group relative rounded-2xl bg-white/[0.025] border ${borderColor} p-4 hover:bg-white/[0.04] transition-all duration-300 overflow-hidden`}
    >
      {/* Gradient accent top edge */}
      <div className={`absolute top-0 left-0 right-0 h-px ${accent}`} />

      {/* Icon + Label Row */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest">{label}</span>
        <div className={`p-2 rounded-xl ${iconBg} transition-transform duration-200 group-hover:scale-110`}>
          <Icon className={`w-4 h-4 ${iconColor}`} />
        </div>
      </div>

      {/* Value */}
      <div className={`text-2xl font-bold stat-value font-mono ${iconColor} leading-none`}>{value}</div>
      {subLabel && <div className="text-[10px] text-slate-500 mt-1 font-medium">{subLabel}</div>}
    </div>
  );
};

export const FleetOverview: React.FC<FleetOverviewProps> = ({ summary }) => {
  const loading = !summary;

  const cards: Omit<KPICardProps, 'loading'>[] = [
    {
      label: 'Total Assets',
      value: summary?.total_machines ?? 0,
      subLabel: 'Monitored machines',
      icon: Layers,
      accent: 'bg-gradient-to-r from-sky-500/60 to-transparent',
      iconBg: 'bg-sky-500/10',
      iconColor: 'text-sky-400',
      borderColor: 'border-sky-500/15 hover:border-sky-500/30',
    },
    {
      label: 'Running',
      value: summary?.running_machines ?? 0,
      subLabel: 'Active production',
      icon: PlayCircle,
      accent: 'bg-gradient-to-r from-emerald-500/60 to-transparent',
      iconBg: 'bg-emerald-500/10',
      iconColor: 'text-emerald-400',
      borderColor: 'border-emerald-500/15 hover:border-emerald-500/30',
    },
    {
      label: 'Stopped / Idle',
      value: summary?.stopped_machines ?? 0,
      subLabel: 'Awaiting activation',
      icon: StopCircle,
      accent: 'bg-gradient-to-r from-slate-500/40 to-transparent',
      iconBg: 'bg-slate-500/10',
      iconColor: 'text-slate-400',
      borderColor: 'border-slate-700/40 hover:border-slate-600/40',
    },
    {
      label: 'Faults / Warnings',
      value: (summary?.fault_machines ?? 0) + (summary?.maintenance_machines ?? 0),
      subLabel: 'Requires attention',
      icon: AlertTriangle,
      accent:
        (summary?.fault_machines ?? 0) > 0
          ? 'bg-gradient-to-r from-rose-500/60 to-transparent'
          : 'bg-gradient-to-r from-amber-500/50 to-transparent',
      iconBg: (summary?.fault_machines ?? 0) > 0 ? 'bg-rose-500/10' : 'bg-amber-500/10',
      iconColor: (summary?.fault_machines ?? 0) > 0 ? 'text-rose-400' : 'text-amber-400',
      borderColor:
        (summary?.fault_machines ?? 0) > 0
          ? 'border-rose-500/20 hover:border-rose-500/40'
          : 'border-amber-500/15 hover:border-amber-500/30',
    },
    {
      label: 'Active Alerts',
      value: summary?.active_alerts_count ?? 0,
      subLabel: 'Unresolved incidents',
      icon: BellRing,
      accent:
        (summary?.active_alerts_count ?? 0) > 0
          ? 'bg-gradient-to-r from-rose-500/60 to-transparent'
          : 'bg-gradient-to-r from-slate-500/30 to-transparent',
      iconBg: (summary?.active_alerts_count ?? 0) > 0 ? 'bg-rose-500/10' : 'bg-slate-500/10',
      iconColor: (summary?.active_alerts_count ?? 0) > 0 ? 'text-rose-400' : 'text-slate-500',
      borderColor:
        (summary?.active_alerts_count ?? 0) > 0
          ? 'border-rose-500/20 hover:border-rose-500/40'
          : 'border-slate-700/40 hover:border-slate-600/40',
    },
    {
      label: 'Avg. Plant Health',
      value: `${(summary?.average_plant_health ?? 0).toFixed(1)}%`,
      subLabel: 'Health score engine',
      icon: Heart,
      accent:
        (summary?.average_plant_health ?? 0) >= 80
          ? 'bg-gradient-to-r from-emerald-500/60 to-transparent'
          : 'bg-gradient-to-r from-amber-500/50 to-transparent',
      iconBg: (summary?.average_plant_health ?? 0) >= 80 ? 'bg-emerald-500/10' : 'bg-amber-500/10',
      iconColor: (summary?.average_plant_health ?? 0) >= 80 ? 'text-emerald-400' : 'text-amber-400',
      borderColor:
        (summary?.average_plant_health ?? 0) >= 80
          ? 'border-emerald-500/15 hover:border-emerald-500/30'
          : 'border-amber-500/15 hover:border-amber-500/30',
    },
    {
      label: 'Plant OEE',
      value: `${(summary?.plant_oee ?? 0).toFixed(1)}%`,
      subLabel: 'Overall Equipment Effectiveness',
      icon: BarChart3,
      accent:
        (summary?.plant_oee ?? 0) >= 75
          ? 'bg-gradient-to-r from-sky-500/60 to-transparent'
          : 'bg-gradient-to-r from-amber-500/50 to-transparent',
      iconBg: (summary?.plant_oee ?? 0) >= 75 ? 'bg-sky-500/10' : 'bg-amber-500/10',
      iconColor: (summary?.plant_oee ?? 0) >= 75 ? 'text-sky-400' : 'text-amber-400',
      borderColor:
        (summary?.plant_oee ?? 0) >= 75
          ? 'border-sky-500/15 hover:border-sky-500/30'
          : 'border-amber-500/15 hover:border-amber-500/30',
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
      {cards.map((card, idx) => (
        <KPICard key={idx} {...card} loading={loading} />
      ))}
    </div>
  );
};
