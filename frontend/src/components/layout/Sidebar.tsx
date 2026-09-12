import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  Network,
  Activity,
  Package,
  Radio,
  Users,
  Pin,
  PinOff,
} from 'lucide-react';

export type NavTabId = 'overview' | 'messages' | 'network' | 'delivery' | 'packet-protection' | 'registry' | 'about';

interface SidebarProps {
  activeTab: NavTabId;
  onTabChange: (tab: NavTabId) => void;
  onPinnedChange?: (pinned: boolean) => void;
}

interface MenuItem {
  id: NavTabId;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  group: 'Main' | 'System';
}

const menuItems: MenuItem[] = [
  { id: 'overview', name: 'Overview', icon: LayoutDashboard, group: 'Main' },
  { id: 'messages', name: 'Emergency Messages', icon: MessageSquare, group: 'Main' },
  { id: 'network', name: 'Network', icon: Network, group: 'Main' },
  { id: 'delivery', name: 'Message Delivery', icon: Activity, group: 'Main' },
  { id: 'packet-protection', name: 'Packet Protection', icon: Package, group: 'Main' },
  { id: 'registry', name: 'Device Registry', icon: Radio, group: 'System' },
  { id: 'about', name: 'About Us', icon: Users, group: 'System' },
];

const groups: ('Main' | 'System')[] = ['Main', 'System'];

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  onPinnedChange,
}) => {
  const [isPinned, setIsPinned] = useState<boolean>(() => {
    return localStorage.getItem('resq_sidebar_pinned') !== 'false';
  });
  const [isHovered, setIsHovered] = useState<boolean>(false);

  useEffect(() => {
    localStorage.setItem('resq_sidebar_pinned', String(isPinned));
    onPinnedChange?.(isPinned);
  }, [isPinned, onPinnedChange]);

  const isOpen = isPinned || isHovered;

  return (
    <aside
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`fixed top-0 left-0 h-screen z-40 bg-slate-900/95 backdrop-blur-md border-r border-slate-800 transition-all duration-300 ease-in-out flex flex-col justify-between ${
        isOpen ? 'w-64 shadow-2xl shadow-indigo-950/20' : 'w-18'
      }`}
    >
      {/* Top Header */}
      <div>
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/80">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-emerald-500 flex items-center justify-center shrink-0 shadow-md shadow-indigo-500/20">
              <Radio className="w-5 h-5 text-white" />
            </div>
            {isOpen && (
              <div className="min-w-0">
                <h1 className="font-black text-sm text-slate-100 tracking-wider truncate">
                  RESQ
                </h1>
                <p className="text-[10px] text-indigo-400 font-bold tracking-widest uppercase">
                  Secure Mesh Network
                </p>
              </div>
            )}
          </div>

          {isOpen && (
            <button
              onClick={() => setIsPinned(!isPinned)}
              title={isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            >
              {isPinned ? <PinOff className="w-4 h-4" /> : <Pin className="w-4 h-4" />}
            </button>
          )}
        </div>

        {/* Nav Links */}
        <div className="p-3 space-y-6">
          {groups.map((group) => {
            const items = menuItems.filter((item) => item.group === group);
            return (
              <div key={group} className="space-y-1">
                {isOpen && (
                  <p className="px-3 text-[11px] font-bold tracking-wider text-slate-400 uppercase mb-2">
                    {group}
                  </p>
                )}
                {items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => onTabChange(item.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group relative ${
                        isActive
                          ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                      }`}
                      title={!isOpen ? item.name : undefined}
                    >
                      <Icon
                        className={`w-5 h-5 shrink-0 transition-colors ${
                          isActive
                            ? 'text-white'
                            : 'text-slate-400 group-hover:text-indigo-400'
                        }`}
                      />
                      {isOpen && (
                        <span className="truncate">{item.name}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer info */}
      <div className="p-4 border-t border-slate-800/80">
        {isOpen ? (
          <div className="bg-slate-800/40 rounded-xl p-3 border border-slate-700/40">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[11px] font-bold text-slate-300">Local Mesh Active</span>
            </div>
            <p className="text-[10px] text-slate-400">Zero-infrastructure emergency routing</p>
          </div>
        ) : (
          <div className="flex justify-center">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 ring-4 ring-emerald-400/20" />
          </div>
        )}
      </div>
    </aside>
  );
};
