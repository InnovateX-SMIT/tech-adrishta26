import React from 'react';
import { AlertCircle } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor?: 'indigo' | 'red' | 'green' | 'amber' | 'cyan';
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  accentColor = 'indigo',
  loading = false,
  error,
  onRetry,
}) => {
  const colorMap = {
    indigo: {
      text: 'text-indigo-400',
      bg: 'bg-indigo-500/10',
      border: 'border-indigo-500/20',
      hover: 'hover:border-indigo-500/40 hover:shadow-[0_0_20px_rgba(99,102,241,0.15)]',
    },
    red: {
      text: 'text-red-400',
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
      hover: 'hover:border-red-500/40 hover:shadow-[0_0_20px_rgba(239,68,68,0.15)]',
    },
    green: {
      text: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
      hover: 'hover:border-emerald-500/40 hover:shadow-[0_0_20px_rgba(34,197,94,0.15)]',
    },
    amber: {
      text: 'text-amber-400',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
      hover: 'hover:border-amber-500/40 hover:shadow-[0_0_20px_rgba(245,158,11,0.15)]',
    },
    cyan: {
      text: 'text-cyan-400',
      bg: 'bg-cyan-500/10',
      border: 'border-cyan-500/20',
      hover: 'hover:border-cyan-500/40 hover:shadow-[0_0_20px_rgba(34,211,238,0.15)]',
    },
  };

  const colors = colorMap[accentColor] || colorMap.indigo;

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-slate-800/60 flex flex-col justify-between min-h-[140px]">
        <div className="flex items-start justify-between">
          <div className="w-10 h-10 bg-slate-800/50 rounded-xl animate-pulse" />
        </div>
        <div>
          <div className="h-3 w-24 bg-slate-800/50 rounded animate-pulse mt-3" />
          <div className="h-8 w-20 bg-slate-800/50 rounded animate-pulse mt-2" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-5 rounded-2xl border-l-4 border-red-500 border border-slate-800/60 flex flex-col justify-between min-h-[140px]">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <h4 className="text-xs font-bold text-red-500 uppercase tracking-wider">Telemetry Error</h4>
            <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">{error}</p>
          </div>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="text-[10px] uppercase font-bold text-indigo-400 hover:text-indigo-300 w-fit cursor-pointer self-end transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={`glass-card p-6 rounded-2xl border border-slate-800/60 flex flex-col justify-between min-h-[140px] relative overflow-hidden transition-all duration-300 ${colors.hover}`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
          {title}
        </span>
        <div className={`p-2.5 rounded-xl border shrink-0 ${colors.bg} ${colors.border}`}>
          <Icon className={`w-5 h-5 ${colors.text}`} />
        </div>
      </div>
      <div>
        <h2 className="text-3xl font-black text-slate-50 tracking-tight leading-none mt-2 font-mono">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </h2>
        {subtitle && (
          <p className="text-[10px] text-slate-500 font-bold tracking-wider mt-1.5 uppercase">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
};
