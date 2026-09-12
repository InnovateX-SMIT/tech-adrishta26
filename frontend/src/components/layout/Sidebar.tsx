import React, { useState, useEffect } from 'react';
import {
  Network,
  ShieldCheck,
  KeyRound,
  Pin,
  PinOff,
  Radio,
  ShieldAlert,
} from 'lucide-react';

export type NavTabId = 'mesh' | 'messages' | 'attack' | 'registry';

interface SidebarProps {
  activeTab: NavTabId;
  onTabChange: (tab: NavTabId) => void;
  onPinnedChange?: (pinned: boolean) => void;
}

interface MenuItem {
  id: NavTabId;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  group: 'Operations' | 'Administration';
  badge?: string;
}

const menuItems: MenuItem[] = [
  { id: 'mesh', name: 'Mesh Simulation', icon: Network, group: 'Operations' },
  { id: 'messages', name: 'Secure Transmit', icon: ShieldCheck, group: 'Operations' },
  { id: 'attack', name: 'Attack Simulation', icon: ShieldAlert, group: 'Operations' },
  { id: 'registry', name: 'Device Registry', icon: KeyRound, group: 'Administration' },
];

const groups: ('Operations' | 'Administration')[] = ['Operations', 'Administration'];

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  onPinnedChange,
}) => {
  const [isPinned, setIsPinned] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('resq_sidebar_pinned') === 'true';
    }
    return false;
  });
  const [isHovering, setIsHovering] = useState<boolean>(false);
  const isOpen = isPinned || isHovering;

  useEffect(() => {
    onPinnedChange?.(isPinned);
  }, [isPinned, onPinnedChange]);

  const togglePinned = () => {
    const next = !isPinned;
    setIsPinned(next);
    sessionStorage.setItem('resq_sidebar_pinned', String(next));
    onPinnedChange?.(next);
  };

  return (
    <aside
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => !isPinned && setIsHovering(false)}
      className={`fixed left-0 top-0 z-50 h-screen bg-[#0a0f1d]/98 border-r border-[#1e293b]/70 text-slate-300 flex flex-col shadow-2xl shadow-black/40 transition-[width] duration-300 ease-out select-none ${
        isOpen ? 'w-64' : 'w-[4.5rem]'
      }`}
    >
      {/* Brand Header */}
      <div
        className={`border-b border-[#1e293b]/50 flex items-center gap-3 ${
          isOpen ? 'p-5 justify-between' : 'px-3 py-5 justify-center'
        }`}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-indigo-600/30 border border-indigo-400/30">
            <Radio className="w-5 h-5 text-white animate-pulse" />
          </div>
          {isOpen && (
            <div className="min-w-0">
              <h1 className="font-black text-sm text-slate-100 tracking-wider truncate">
                RESQ MESH
              </h1>
              <p className="text-[10px] text-indigo-400 font-bold tracking-widest uppercase">
                Zero-Trust P2P
              </p>
            </div>
          )}
        </div>

        {isOpen && (
          <button
            type="button"
            onClick={togglePinned}
            className="p-2 rounded-lg border border-slate-800 bg-slate-950/60 text-slate-500 hover:text-indigo-300 hover:border-indigo-500/30 transition-colors cursor-pointer"
            aria-label={isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
            title={isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
          >
            {isPinned ? <PinOff className="w-4 h-4" /> : <Pin className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Navigation Groupings */}
      <nav className={`flex-1 py-4 overflow-y-auto ${isOpen ? 'px-4 space-y-6' : 'px-2 space-y-4'}`}>
        {groups.map((group) => {
          const items = menuItems.filter((item) => item.group === group);
          return (
            <div key={group}>
              {isOpen && (
                <div className="text-[9px] uppercase font-bold text-slate-600 tracking-widest px-3 mb-2">
                  {group}
                </div>
              )}
              <div className="space-y-1">
                {items.map((item) => {
                  const isActive = activeTab === item.id;
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => onTabChange(item.id)}
                      title={item.name}
                      aria-label={item.name}
                      className={`w-full flex items-center rounded-xl text-sm font-medium transition-all duration-200 group border cursor-pointer ${
                        isOpen ? 'justify-start gap-3 px-3 py-2.5' : 'justify-center h-11 w-11 mx-auto'
                      } ${
                        isActive
                          ? 'bg-indigo-600/10 text-indigo-400 border-indigo-500/30 shadow-[inset_0_1px_0_rgba(99,102,241,0.15)] font-bold'
                          : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border-transparent'
                      }`}
                    >
                      <Icon
                        className={`w-4 h-4 transition-colors shrink-0 ${
                          isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'
                        }`}
                      />
                      {isOpen && (
                        <div className="flex items-center justify-between flex-1 min-w-0">
                          <span className="truncate">{item.name}</span>
                          {item.badge && (
                            <span className="text-[9px] font-mono px-1.5 py-0.2 rounded border bg-indigo-500/10 border-indigo-500/20 text-indigo-400 font-bold uppercase tracking-wider">
                              {item.badge}
                            </span>
                          )}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>

      {/* Collapsed Pin Button in Footer */}
      {!isOpen && (
        <div className="border-t border-slate-800/60 p-3">
          <button
            type="button"
            onClick={togglePinned}
            className="h-11 w-11 mx-auto flex items-center justify-center rounded-xl border border-slate-800 bg-slate-950/60 text-slate-500 hover:text-indigo-300 hover:border-indigo-500/30 transition-colors cursor-pointer"
            aria-label={isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
            title={isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
          >
            {isPinned ? <PinOff className="w-4 h-4" /> : <Pin className="w-4 h-4" />}
          </button>
        </div>
      )}
    </aside>
  );
};
