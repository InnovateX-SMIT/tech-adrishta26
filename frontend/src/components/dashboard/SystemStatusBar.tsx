import React from 'react';
import { ShieldCheck, Cpu } from 'lucide-react';

interface SystemStatusBarProps {
  nodeCount: number;
  edgeCount: number;
  isBackendConnected: boolean;
  lastPingTime?: string | null;
  deliveredPacketsCount?: number;
}

export const SystemStatusBar: React.FC<SystemStatusBarProps> = ({
  nodeCount,
  edgeCount,
  isBackendConnected,
  lastPingTime,
  deliveredPacketsCount = 0,
}) => {
  return (
    <div className="glass-card p-5 rounded-2xl border border-slate-800/60 w-full flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4 divide-y md:divide-y-0 md:divide-x divide-slate-800/60 select-none">
      {/* 1. Simulation Engine State */}
      <div className="flex-1 flex items-center gap-3 md:pb-0 pb-3">
        <div className="relative flex h-2.5 w-2.5 shrink-0">
          {isBackendConnected ? (
            <>
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </>
          ) : (
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
          )}
        </div>
        <div>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
            Simulation Network
          </p>
          <p className={`text-xs font-black tracking-tight ${isBackendConnected ? 'text-emerald-400' : 'text-red-400'}`}>
            {isBackendConnected ? 'ACTIVE ONLINE' : 'DISCONNECTED'}
          </p>
        </div>
      </div>

      {/* 2. Topology Density */}
      <div className="flex-1 flex flex-col justify-center md:pl-6 md:pb-0 py-3">
        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
          Topology Density
        </p>
        <p className="text-xs font-extrabold text-slate-200 mt-0.5 tracking-tight font-mono">
          {nodeCount} <span className="text-[10px] text-slate-400 font-semibold uppercase">Nodes</span>
          <span className="text-slate-600 mx-1.5">•</span>
          {edgeCount} <span className="text-[10px] text-slate-400 font-semibold uppercase">Links</span>
        </p>
      </div>

      {/* 3. Cryptographic Guard */}
      <div className="flex-1 flex flex-col justify-center md:pl-6 md:pb-0 py-3">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
            Security Layer
          </p>
        </div>
        <p className="text-xs font-bold text-slate-200 mt-0.5 tracking-tight font-mono truncate">
          AES-256-GCM + Ed25519
        </p>
      </div>

      {/* 4. Packets / Telemetry Sync */}
      <div className="flex-1 flex flex-col justify-center md:pl-6 md:pt-0 pt-3">
        <div className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
            Telemetry Freshness
          </p>
        </div>
        <p className="text-xs font-mono font-bold text-cyan-400 mt-0.5 tracking-tight">
          {lastPingTime || 'Syncing...'}
          {deliveredPacketsCount > 0 && (
            <span className="text-[10px] text-slate-400 font-normal ml-2">
              ({deliveredPacketsCount} pkts)
            </span>
          )}
        </p>
      </div>
    </div>
  );
};
