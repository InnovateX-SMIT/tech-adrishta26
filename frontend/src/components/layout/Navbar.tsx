import React from 'react';
import { RefreshCw, AlertCircle, Radio, Bell } from 'lucide-react';
import { NavTabId } from './Sidebar';

interface NavbarProps {
  activeTab: NavTabId;
  isConnected: boolean;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

const TAB_TITLES: Record<NavTabId, string> = {
  mesh: 'Mesh Simulation & Routing',
  messages: 'Secure Cryptographic Messaging',
  registry: 'Rescue Device & Key Registry',
  roadmap: 'Architecture & Phase Roadmap',
};

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  isConnected,
  onRefresh,
  isRefreshing = false,
}) => {
  return (
    <header
      role="banner"
      className="h-14 border-b border-slate-800/60 bg-[#070b13]/90 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between gap-4 select-none"
    >
      {/* Left: Live Status Pill & Breadcrumb */}
      <div className="flex items-center gap-4 min-w-0">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-800/60 text-xs shrink-0">
          <Radio className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-500 font-semibold hidden sm:inline">MESH API</span>
          {isConnected ? (
            <span className="text-emerald-400 font-bold flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span className="hidden sm:inline">LIVE</span>
            </span>
          ) : (
            <span className="text-red-400 font-bold flex items-center gap-1.5">
              <AlertCircle className="w-3 h-3 text-red-400 animate-pulse" />
              <span className="hidden sm:inline">DISCONNECTED</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500 min-w-0">
          <span className="text-slate-600 font-semibold hidden sm:inline">RESQ</span>
          <span className="text-slate-700 hidden sm:inline">/</span>
          <span className="font-bold text-slate-200 truncate">
            {TAB_TITLES[activeTab] || 'Emergency System'}
          </span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1.5 shrink-0">
        <button
          type="button"
          onClick={onRefresh}
          disabled={isRefreshing}
          aria-label="Refresh telemetry data"
          title="Refresh Telemetry"
          className="text-slate-400 hover:text-slate-100 transition-colors p-2 rounded-xl hover:bg-slate-800/60 border border-transparent hover:border-slate-800 focus-visible:ring-1 focus-visible:ring-indigo-500 cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
        </button>

        <div className="relative">
          <button
            type="button"
            aria-label="System telemetry notifications"
            title="System Telemetry Alerts"
            className="text-slate-400 hover:text-slate-100 transition-colors p-2 rounded-xl hover:bg-slate-800/60 border border-transparent hover:border-slate-800 cursor-pointer"
          >
            <Bell className="w-4 h-4" />
            <span
              className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-500 rounded-full ring-2 ring-[#070b13]"
              aria-hidden="true"
            />
          </button>
        </div>
      </div>
    </header>
  );
};
