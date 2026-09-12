import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  Radio,
  Lock,
  Unlock,
  Eye,
  EyeOff,
  Zap,
  ArrowRight,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Terminal,
  Network,
  Send,
  ShieldAlert,
  KeyRound,
  Activity,
  Wifi,
  WifiOff,
  ChevronRight,
  Cpu,
  TriangleAlert,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type {
  DashboardOverviewResponse,
  DashboardNodeSummary,
  QuickDispatchResponse,
} from '../../types';

// ─── Telemetry Log Entry ───────────────────────────────────────────────────

interface LogEntry {
  id: string;
  ts: string;
  level: 'info' | 'success' | 'warn' | 'error' | 'crypto';
  msg: string;
}

function tsNow(): string {
  return new Date().toLocaleTimeString('en-US', { hour12: false });
}

function makeLog(level: LogEntry['level'], msg: string): LogEntry {
  return { id: `${Date.now()}-${Math.random()}`, ts: tsNow(), level, msg };
}

// ─── Operational Status Bar ───────────────────────────────────────────────

interface StatusPillProps {
  label: string;
  value: string;
  state: 'good' | 'bad' | 'secure' | 'verified' | 'enforced';
  icon: React.ReactNode;
}

const StatusPill: React.FC<StatusPillProps> = ({ label, value, state, icon }) => {
  const colors: Record<string, string> = {
    good: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 shadow-emerald-500/10',
    bad: 'bg-red-500/10 border-red-500/30 text-red-300 shadow-red-500/10',
    secure: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300 shadow-cyan-500/10',
    verified: 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300 shadow-indigo-500/10',
    enforced: 'bg-violet-500/10 border-violet-500/30 text-violet-300 shadow-violet-500/10',
  };
  const dotColors: Record<string, string> = {
    good: 'bg-emerald-400',
    bad: 'bg-red-400',
    secure: 'bg-cyan-400',
    verified: 'bg-indigo-400',
    enforced: 'bg-violet-400',
  };

  return (
    <div
      className={`flex items-center gap-2.5 px-3 py-2 rounded-xl border text-xs font-bold shadow-lg ${colors[state]}`}
    >
      <span className="shrink-0">{icon}</span>
      <div className="min-w-0">
        <div className="text-[9px] uppercase tracking-widest opacity-60 font-semibold leading-none mb-0.5">
          {label}
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className={`relative flex h-1.5 w-1.5 shrink-0`}
          >
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dotColors[state]}`}
            />
            <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${dotColors[state]}`} />
          </span>
          <span className="truncate">{value}</span>
        </div>
      </div>
    </div>
  );
};

// ─── Mesh Node Card ───────────────────────────────────────────────────────

const NodeCard: React.FC<{ node: DashboardNodeSummary; isActiveRoute: boolean; isSource: boolean; isDest: boolean }> = ({
  node,
  isActiveRoute,
  isSource,
  isDest,
}) => {
  let borderClass = 'border-slate-800/60';
  let glowClass = '';
  let roleLabel = '';
  let roleColor = 'text-slate-400';

  if (node.is_attacker) {
    borderClass = 'border-red-500/30';
    glowClass = 'shadow-[0_0_12px_rgba(239,68,68,0.15)]';
    roleLabel = 'ATTACKER';
    roleColor = 'text-red-400';
  } else if (isSource) {
    borderClass = 'border-emerald-500/40';
    glowClass = 'shadow-[0_0_12px_rgba(16,185,129,0.2)]';
    roleLabel = 'SENDER';
    roleColor = 'text-emerald-400';
  } else if (isDest) {
    borderClass = 'border-indigo-500/40';
    glowClass = 'shadow-[0_0_12px_rgba(99,102,241,0.2)]';
    roleLabel = 'RECEIVER';
    roleColor = 'text-indigo-400';
  } else if (isActiveRoute) {
    borderClass = 'border-amber-500/30';
    glowClass = 'shadow-[0_0_8px_rgba(245,158,11,0.1)]';
    roleLabel = 'RELAY';
    roleColor = 'text-amber-400';
  }

  return (
    <div
      className={`relative bg-slate-900/50 border rounded-xl p-3 flex flex-col gap-1.5 transition-all duration-300 ${borderClass} ${glowClass}`}
    >
      {!node.is_online && (
        <div className="absolute inset-0 bg-slate-950/60 rounded-xl flex items-center justify-center">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">OFFLINE</span>
        </div>
      )}
      <div className="flex items-center justify-between gap-2">
        <div
          className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
            node.is_attacker ? 'bg-red-500/10' : 'bg-slate-800'
          }`}
        >
          {node.is_attacker ? (
            <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
          ) : (
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
          )}
        </div>
        <span className={`text-[9px] font-black uppercase tracking-wider ${roleColor}`}>{roleLabel}</span>
      </div>
      <div>
        <div className="text-[10px] font-black text-slate-100 truncate">{node.node_id}</div>
        <div className="text-[9px] text-slate-500 font-mono truncate">{node.name}</div>
      </div>
      <div className="flex items-center gap-1.5 flex-wrap">
        {node.is_keyed && (
          <span className="px-1.5 py-0.5 bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[8px] font-bold rounded uppercase tracking-wider">
            KEYED
          </span>
        )}
        {node.is_online ? (
          <span className="px-1.5 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[8px] font-bold rounded uppercase tracking-wider">
            ONLINE
          </span>
        ) : (
          <span className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 text-slate-500 text-[8px] font-bold rounded uppercase tracking-wider">
            DOWN
          </span>
        )}
      </div>
    </div>
  );
};

// ─── Route Breadcrumb ─────────────────────────────────────────────────────

const RouteBreadcrumb: React.FC<{ hops: string[]; status: string }> = ({ hops, status }) => {
  if (!hops || hops.length === 0) return null;
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {hops.map((hop, i) => (
        <React.Fragment key={i}>
          <span className="px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[9px] font-mono font-bold rounded">
            {hop}
          </span>
          {i < hops.length - 1 && <ChevronRight className="w-3 h-3 text-slate-600 shrink-0" />}
        </React.Fragment>
      ))}
      <span
        className={`ml-1 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider ${
          status === 'DELIVERED' || status === 'delivered'
            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
        }`}
      >
        {status}
      </span>
    </div>
  );
};

// ─── Gate Step ────────────────────────────────────────────────────────────

const GateStep: React.FC<{ label: string; status: 'pass' | 'fail' | 'pending' }> = ({ label, status }) => {
  const cfg = {
    pass: { icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />, text: 'text-emerald-300', bg: 'bg-emerald-500/5 border-emerald-500/20' },
    fail: { icon: <XCircle className="w-3.5 h-3.5 text-red-400" />, text: 'text-red-300', bg: 'bg-red-500/5 border-red-500/20' },
    pending: { icon: <Activity className="w-3.5 h-3.5 text-slate-500 animate-pulse" />, text: 'text-slate-500', bg: 'bg-slate-900 border-slate-800' },
  }[status];

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-[10px] font-bold ${cfg.bg} ${cfg.text}`}>
      {cfg.icon}
      {label}
    </div>
  );
};

// ─── Log Level Colors ─────────────────────────────────────────────────────

const LOG_COLORS: Record<LogEntry['level'], string> = {
  info: 'text-slate-400',
  success: 'text-emerald-400',
  warn: 'text-amber-400',
  error: 'text-red-400',
  crypto: 'text-cyan-400',
};
const LOG_PREFIXES: Record<LogEntry['level'], string> = {
  info: '[INF]',
  success: '[OK ]',
  warn: '[WRN]',
  error: '[ERR]',
  crypto: '[ENC]',
};

// ─── Dispatch Preset Messages ──────────────────────────────────────────────

const DISPATCH_PRESETS = [
  'SOS: Building B Collapse — 3 trapped, air supply 20 min.',
  'MAYDAY: Medical transport needed at Grid 4-Alpha.',
  'CORRIDOR CHARLIE: Fire spreading east wing, evacuate now.',
  'STATUS UPDATE: Search team at sector 7, all clear.',
];

// ═══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export const TacticalCommandDashboard: React.FC = () => {
  const [overview, setOverview] = useState<DashboardOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [dispatching, setDispatching] = useState(false);
  const [lastDispatch, setLastDispatch] = useState<QuickDispatchResponse | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  // Dispatch form state
  const [dispatchMode, setDispatchMode] = useState<'protected' | 'vulnerable'>('protected');
  const [dispatchMsg, setDispatchMsg] = useState(DISPATCH_PRESETS[0]);
  const [senderId, setSenderId] = useState('RESQ-001');
  const [recipientId, setRecipientId] = useState('RESQ-002');

  const pushLog = useCallback((level: LogEntry['level'], msg: string) => {
    setLogs((prev) => [makeLog(level, msg), ...prev].slice(0, 60));
  }, []);

  const fetchOverview = useCallback(async () => {
    try {
      const data = await apiService.getDashboardOverview();
      setOverview(data);
      pushLog('info', `Telemetry refreshed — ${data.nodes.length} nodes online, ${data.messaging.total_messages} total msgs`);
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Failed to fetch dashboard telemetry');
    } finally {
      setLoading(false);
    }
  }, [pushLog]);

  // Initial load + 3-second auto-refresh
  useEffect(() => {
    fetchOverview();
    const interval = setInterval(fetchOverview, 3000);
    return () => clearInterval(interval);
  }, [fetchOverview]);

  // Auto-scroll log to top when new entries arrive
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = 0;
  }, [logs]);

  const handleDispatch = async () => {
    if (dispatching) return;
    setDispatching(true);
    setLastDispatch(null);
    pushLog('info', `Dispatching [${dispatchMode.toUpperCase()}] — Sender: ${senderId} → Recipient: ${recipientId}`);
    try {
      const result = await apiService.quickDispatchMessage({
        mode: dispatchMode,
        sender_id: senderId,
        recipient_id: recipientId,
        message: dispatchMsg,
      });
      setLastDispatch(result);
      setOverview(result.overview);

      if (dispatchMode === 'protected') {
        pushLog('crypto', `Packet ${result.packet_id} — Encrypted with ChaCha20-Poly1305, Signed with Ed25519`);
        pushLog('warn', `Attacker tapped: ${result.attacker_sniffed.slice(0, 60)}...`);
        pushLog('success', `Gate Decision: ${result.security_gate_decision} — Plaintext delivered to ${recipientId}`);
      } else {
        pushLog('error', `VULNERABLE dispatch — plaintext exposed on wire!`);
        pushLog('warn', `Attacker captured: "${result.attacker_sniffed.slice(0, 80)}"`);
        pushLog('success', `Delivery complete — mode: INSECURE`);
      }
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Dispatch failed');
    } finally {
      setDispatching(false);
    }
  };

  // Derive gate steps from last dispatch
  const gateSteps = lastDispatch
    ? ([
        ['Registry Lookup', lastDispatch.security_gate_decision !== 'UNAUTHORIZED' ? 'pass' : 'fail'],
        ['Status Check', lastDispatch.security_gate_decision !== 'UNAUTHORIZED' ? 'pass' : 'fail'],
        ['Signature Verify', lastDispatch.security_gate_decision !== 'SIGNATURE_FAILED' ? 'pass' : 'fail'],
        ['Recipient Access', lastDispatch.security_gate_decision === 'AUTHORIZED_DECRYPTED' ? 'pass' : 'fail'],
        ['Controlled Decrypt', lastDispatch.security_gate_decision === 'AUTHORIZED_DECRYPTED' ? 'pass' : 'fail'],
      ] as [string, 'pass' | 'fail'][])
    : [];

  const activeRoute = overview?.active_route;
  const attacker = overview?.attacker;
  const security = overview?.security;
  const messaging = overview?.messaging;
  const ops = overview?.operational_status;
  const nodes = overview?.nodes ?? [];

  // Figure out sender/receiver node IDs for route highlighting
  const sourceNodeId = activeRoute?.source ?? '';
  const destNodeId = activeRoute?.destination ?? '';
  const routeHops = new Set(activeRoute?.hops ?? []);

  return (
    <div className="space-y-5 animate-fade-in">
      {/* ── TOP: Blackout & Operational Status Bar ──────────────────────── */}
      <div className="glass-card rounded-2xl border border-slate-800/60 p-4">
        <div className="flex flex-col lg:flex-row lg:items-center gap-3">
          <div className="flex items-center gap-2 shrink-0">
            <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/20">
              <WifiOff className="w-4 h-4 text-red-400" />
            </div>
            <div>
              <div className="text-[10px] font-black text-red-400 uppercase tracking-widest">
                ⚠ BLACKOUT ACTIVE
              </div>
              <div className="text-[9px] text-slate-500 font-mono">Cellular & Cloud Infrastructure: OFFLINE</div>
            </div>
          </div>

          <div className="hidden lg:block w-px h-8 bg-slate-800 shrink-0" />

          <div className="flex flex-wrap gap-2 flex-1 min-w-0">
            <StatusPill
              label="Cellular Network"
              value={ops?.cellular_network ?? 'OFFLINE (Blackout Active)'}
              state="bad"
              icon={<WifiOff className="w-3.5 h-3.5" />}
            />
            <StatusPill
              label="Emergency Mesh"
              value={ops?.emergency_mesh ?? 'ACTIVE'}
              state="good"
              icon={<Radio className="w-3.5 h-3.5" />}
            />
            <StatusPill
              label="Zero-Trust Encryption"
              value={ops?.encryption ?? 'ACTIVE (ChaCha20-Poly1305)'}
              state="secure"
              icon={<Lock className="w-3.5 h-3.5" />}
            />
            <StatusPill
              label="Identity Authority"
              value={ops?.identity_authority ?? 'VERIFIED (Ed25519)'}
              state="verified"
              icon={<ShieldCheck className="w-3.5 h-3.5" />}
            />
            <StatusPill
              label="Controlled Decryption"
              value={ops?.controlled_decryption ?? 'ENFORCED'}
              state="enforced"
              icon={<KeyRound className="w-3.5 h-3.5" />}
            />
          </div>

          <div className="flex items-center gap-2 shrink-0 ml-auto">
            {loading ? (
              <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin" />
            ) : (
              <Wifi className="w-4 h-4 text-emerald-400" />
            )}
            <span className="text-[10px] text-emerald-400 font-mono font-bold">SYSTEM ACTIVE</span>
          </div>
        </div>
      </div>

      {/* ── 4-PILLAR GRID ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        {/* ── PILLAR 1: Mesh Network Topology ──────────────────────────── */}
        <div className="glass-card rounded-2xl border border-slate-800/60 p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
              <Network className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-sm font-black text-slate-100 uppercase tracking-tight">
                Mesh Network Topology
              </h2>
              <p className="text-[10px] text-slate-500">
                {nodes.length} nodes · {overview?.edges?.length ?? 0} links · Live ad-hoc routing
              </p>
            </div>
          </div>

          {/* Node Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {nodes.length === 0 ? (
              <div className="col-span-3 py-8 text-center text-slate-600 text-xs animate-pulse">
                Fetching mesh topology...
              </div>
            ) : (
              nodes.map((node) => (
                <NodeCard
                  key={node.node_id}
                  node={node}
                  isActiveRoute={routeHops.has(node.node_id)}
                  isSource={node.node_id === sourceNodeId}
                  isDest={node.node_id === destNodeId}
                />
              ))
            )}
          </div>

          {/* Active Route Breadcrumb */}
          {activeRoute && (
            <div className="space-y-2 pt-1 border-t border-slate-800/60">
              <div className="text-[9px] uppercase font-bold text-slate-500 tracking-wider">
                Last Active Route — {activeRoute.route_id}
              </div>
              <RouteBreadcrumb hops={activeRoute.hops} status={activeRoute.status} />
              <div className="text-[9px] text-slate-600 font-mono">
                {activeRoute.hop_count} hops · {activeRoute.source} → {activeRoute.destination}
              </div>
            </div>
          )}
        </div>

        {/* ── PILLAR 2: Emergency Messaging Terminal ───────────────────── */}
        <div className="glass-card rounded-2xl border border-slate-800/60 p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <Send className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-sm font-black text-slate-100 uppercase tracking-tight">
                Emergency Messaging Terminal
              </h2>
              <p className="text-[10px] text-slate-500">
                {messaging?.total_messages ?? 0} total · {messaging?.delivered_count ?? 0} delivered · {messaging?.in_transit_count ?? 0} in-transit
              </p>
            </div>
          </div>

          {/* IDs */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[9px] uppercase tracking-widest font-bold text-slate-500 mb-1">
                Sender ID
              </label>
              <input
                type="text"
                value={senderId}
                onChange={(e) => setSenderId(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono outline-none focus:border-emerald-500/50 transition-colors"
                placeholder="RESQ-001"
              />
            </div>
            <div>
              <label className="block text-[9px] uppercase tracking-widest font-bold text-slate-500 mb-1">
                Recipient ID
              </label>
              <input
                type="text"
                value={recipientId}
                onChange={(e) => setRecipientId(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono outline-none focus:border-emerald-500/50 transition-colors"
                placeholder="RESQ-002"
              />
            </div>
          </div>

          {/* Presets */}
          <div className="space-y-1">
            <div className="text-[9px] uppercase tracking-widest font-bold text-slate-500">Quick Presets</div>
            <div className="grid grid-cols-1 gap-1">
              {DISPATCH_PRESETS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setDispatchMsg(preset)}
                  className={`text-left px-3 py-1.5 rounded-lg text-[10px] font-medium transition-all cursor-pointer border ${
                    dispatchMsg === preset
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                  }`}
                >
                  <Zap className="w-2.5 h-2.5 inline mr-1.5 shrink-0" />
                  {preset}
                </button>
              ))}
            </div>
          </div>

          {/* Mode Toggle */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setDispatchMode('protected')}
              className={`flex-1 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider border transition-all cursor-pointer ${
                dispatchMode === 'protected'
                  ? 'bg-emerald-600/20 border-emerald-500/40 text-emerald-300'
                  : 'bg-slate-900/40 border-slate-800 text-slate-500 hover:text-slate-300'
              }`}
            >
              🔐 Protected
            </button>
            <button
              type="button"
              onClick={() => setDispatchMode('vulnerable')}
              className={`flex-1 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider border transition-all cursor-pointer ${
                dispatchMode === 'vulnerable'
                  ? 'bg-red-500/20 border-red-500/40 text-red-300'
                  : 'bg-slate-900/40 border-slate-800 text-slate-500 hover:text-slate-300'
              }`}
            >
              ⚠ Vulnerable
            </button>
          </div>

          {/* Dispatch Button */}
          <button
            type="button"
            onClick={handleDispatch}
            disabled={dispatching}
            className={`w-full py-3 rounded-xl font-black uppercase tracking-wider text-xs transition-all cursor-pointer flex items-center justify-center gap-2 shadow-lg disabled:opacity-60 disabled:cursor-not-allowed ${
              dispatchMode === 'protected'
                ? 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white shadow-emerald-600/20'
                : 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white shadow-red-600/20'
            }`}
          >
            {dispatching ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Dispatching across Mesh...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Dispatch Distress Message
              </>
            )}
          </button>

          {/* Last Dispatch Route */}
          {lastDispatch && (
            <div className="pt-2 border-t border-slate-800/60 space-y-1.5">
              <div className="text-[9px] uppercase tracking-wider font-bold text-slate-500">Last Dispatch Route</div>
              <div className="flex items-center gap-1 flex-wrap">
                {lastDispatch.route.map((hop, i) => (
                  <React.Fragment key={i}>
                    <span className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 text-slate-300 text-[9px] font-mono rounded">
                      {hop}
                    </span>
                    {i < lastDispatch.route.length - 1 && (
                      <ArrowRight className="w-2.5 h-2.5 text-slate-600 shrink-0" />
                    )}
                  </React.Fragment>
                ))}
                <span className="text-[9px] text-slate-500 ml-1">({lastDispatch.hop_count} hops)</span>
              </div>
            </div>
          )}
        </div>

        {/* ── PILLAR 3: Cryptographic Security & Decryption Gate ──────── */}
        <div className="glass-card rounded-2xl border border-slate-800/60 p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
              <ShieldCheck className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-sm font-black text-slate-100 uppercase tracking-tight">
                Cryptographic Security & Decryption Gate
              </h2>
              <p className="text-[10px] text-slate-500">
                {security?.keyed_devices_count ?? 0} keyed devices · {security?.active_responders_count ?? 0} active responders · Gate pass: {security?.gate_success_rate ?? 100}%
              </p>
            </div>
          </div>

          {/* Gate Steps */}
          <div className="space-y-1.5">
            <div className="text-[9px] uppercase tracking-widest font-bold text-slate-500">Authorization Gate Pipeline</div>
            <div className="flex flex-wrap items-center gap-1.5">
              {lastDispatch ? (
                gateSteps.map(([label, status], i) => (
                  <React.Fragment key={i}>
                    <GateStep label={label} status={status} />
                    {i < gateSteps.length - 1 && <ChevronRight className="w-3 h-3 text-slate-700 shrink-0" />}
                  </React.Fragment>
                ))
              ) : (
                ['Registry', 'Status', 'Signature', 'Recipient Access', 'Decryption'].map((step, i, arr) => (
                  <React.Fragment key={i}>
                    <GateStep label={step} status="pending" />
                    {i < arr.length - 1 && <ChevronRight className="w-3 h-3 text-slate-700 shrink-0" />}
                  </React.Fragment>
                ))
              )}
            </div>
          </div>

          {/* Decryption Result */}
          {lastDispatch?.decrypted_message && lastDispatch.security_gate_decision === 'AUTHORIZED_DECRYPTED' && (
            <div className="bg-emerald-500/8 border border-emerald-500/25 rounded-xl p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Unlock className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-[10px] font-black uppercase tracking-wider text-emerald-400">
                  🔓 Authorized — Message Decrypted
                </span>
              </div>
              <p className="text-xs text-emerald-300 font-semibold leading-relaxed">
                "{lastDispatch.decrypted_message}"
              </p>
              <div className="text-[9px] text-emerald-500/70 font-mono">
                Sender identity verified · Payload authenticated · Access granted
              </div>
            </div>
          )}

          {lastDispatch && lastDispatch.security_gate_decision !== 'AUTHORIZED_DECRYPTED' && (
            <div className="bg-amber-500/8 border border-amber-500/25 rounded-xl p-4 flex items-center gap-3">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <div>
                <div className="text-[10px] font-black text-amber-400 uppercase tracking-wider">
                  Gate Decision: {lastDispatch.security_gate_decision}
                </div>
                <div className="text-[9px] text-amber-500/70">
                  {lastDispatch.explanation}
                </div>
              </div>
            </div>
          )}

          {!lastDispatch && (
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex items-center gap-3">
              <Activity className="w-4 h-4 text-slate-600 animate-pulse shrink-0" />
              <p className="text-[10px] text-slate-600">
                Dispatch a message to run the authorization gate pipeline.
              </p>
            </div>
          )}

          {/* Security Events */}
          {security && security.recent_security_events.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[9px] uppercase tracking-widest font-bold text-slate-500">Recent Security Events</div>
              <div className="space-y-1 max-h-[120px] overflow-y-auto pr-1">
                {security.recent_security_events.map((evt, i) => (
                  <div key={i} className="text-[9px] font-mono text-slate-500 bg-slate-900/40 px-2 py-1 rounded border border-slate-800/60 truncate">
                    {evt}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── PILLAR 4: Attacker Packet-Sniffing Monitor ───────────────── */}
        <div className="glass-card rounded-2xl border border-slate-800/60 p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/20">
              <Eye className="w-4 h-4 text-red-400" />
            </div>
            <div>
              <h2 className="text-sm font-black text-slate-100 uppercase tracking-tight">
                Attacker Packet-Sniffing Monitor
              </h2>
              <p className="text-[10px] text-slate-500">
                Sniffer node: <span className="font-mono text-red-400">{attacker?.attacker_node_id ?? 'DEVICE-004'}</span> · {attacker?.total_intercepted ?? 0} captured
              </p>
            </div>
          </div>

          {/* Capture Stats */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-3 text-center">
              <div className="text-lg font-black text-slate-100">{attacker?.total_intercepted ?? 0}</div>
              <div className="text-[9px] text-slate-500 uppercase tracking-wider font-bold mt-0.5">Total Captured</div>
            </div>
            <div className="bg-emerald-500/5 border border-emerald-500/15 rounded-xl p-3 text-center">
              <div className="text-lg font-black text-emerald-400">{attacker?.protected_captures ?? 0}</div>
              <div className="text-[9px] text-emerald-500 uppercase tracking-wider font-bold mt-0.5">Protected</div>
            </div>
            <div className="bg-red-500/5 border border-red-500/15 rounded-xl p-3 text-center">
              <div className="text-lg font-black text-red-400">{attacker?.vulnerable_captures ?? 0}</div>
              <div className="text-[9px] text-red-500 uppercase tracking-wider font-bold mt-0.5">Vulnerable</div>
            </div>
          </div>

          {/* Side-by-side: Protected vs Vulnerable */}
          {lastDispatch && (
            <div className="space-y-2">
              <div className="text-[9px] uppercase tracking-widest font-bold text-slate-500">
                Latest Capture — Wire Content vs. Attacker Readability
              </div>
              <div className="grid grid-cols-1 gap-2">
                {/* Wire Content */}
                <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <EyeOff className="w-3 h-3 text-slate-500" />
                    <span className="text-[9px] font-black uppercase tracking-wider text-slate-400">
                      Wire-Level Capture (What attacker sees on wire)
                    </span>
                  </div>
                  <div className="font-mono text-[9px] text-slate-400 bg-black/40 px-2.5 py-2 rounded-lg break-all leading-relaxed max-h-16 overflow-y-auto">
                    {lastDispatch.attacker_sniffed}
                  </div>
                </div>

                {/* Verdict */}
                <div
                  className={`rounded-xl p-3 border flex items-center gap-3 ${
                    lastDispatch.attacker_readable
                      ? 'bg-red-500/10 border-red-500/30'
                      : 'bg-emerald-500/8 border-emerald-500/20'
                  }`}
                >
                  {lastDispatch.attacker_readable ? (
                    <TriangleAlert className="w-5 h-5 text-red-400 shrink-0" />
                  ) : (
                    <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                  )}
                  <div>
                    <div
                      className={`text-[10px] font-black uppercase tracking-wider ${
                        lastDispatch.attacker_readable ? 'text-red-300' : 'text-emerald-300'
                      }`}
                    >
                      Attacker Captured: {lastDispatch.captured_by_attacker ? 'YES' : 'NO'} &nbsp;|&nbsp; Plaintext Exposed:{' '}
                      {lastDispatch.attacker_readable ? (
                        <span className="text-red-400">YES ⚠</span>
                      ) : (
                        <span className="text-emerald-400">NO ✓</span>
                      )}
                    </div>
                    <div
                      className={`text-[9px] font-medium mt-0.5 ${
                        lastDispatch.attacker_readable ? 'text-red-400/70' : 'text-emerald-500/70'
                      }`}
                    >
                      {lastDispatch.explanation}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {!lastDispatch && (
            <div className="space-y-2">
              <div className="text-[9px] uppercase tracking-widest font-bold text-slate-500">Attacker Readability Verdict</div>
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex items-center gap-3">
                <Eye className="w-4 h-4 text-slate-600 shrink-0" />
                <p className="text-[10px] text-slate-600">
                  {attacker?.readability_verdict ?? 'No packets intercepted yet. Dispatch a message to trigger sniffing.'}
                </p>
              </div>
            </div>
          )}

          {/* Summary Takeaway */}
          <div className="bg-indigo-500/5 border border-indigo-500/15 rounded-xl p-3">
            <p className="text-[9px] text-indigo-300/70 italic font-medium">
              💡 "{overview?.summary_takeaway ?? 'The goal is not to prevent packet capture. The goal is to ensure that capturing a packet does not reveal the emergency message.'}"
            </p>
          </div>
        </div>
      </div>

      {/* ── LIVE TELEMETRY EVENT LOG ─────────────────────────────────────── */}
      <div className="glass-card rounded-2xl border border-slate-800/60 p-5 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-slate-800 border border-slate-700">
              <Terminal className="w-4 h-4 text-slate-400" />
            </div>
            <div>
              <h2 className="text-sm font-black text-slate-100 uppercase tracking-tight">
                Live Telemetry Event Log
              </h2>
              <p className="text-[10px] text-slate-500">Color-coded real-time security & network events</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setLogs([])}
            className="text-[9px] text-slate-600 hover:text-slate-400 uppercase tracking-wider font-bold transition-colors cursor-pointer"
          >
            Clear
          </button>
        </div>

        <div
          ref={logRef}
          className="h-44 overflow-y-auto bg-black/40 border border-slate-900 rounded-xl p-3 space-y-0.5 font-mono text-[10px] scrollbar-thin"
        >
          {logs.length === 0 ? (
            <div className="text-slate-700 animate-pulse">Awaiting system events...</div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="flex items-start gap-2 leading-relaxed">
                <span className="text-slate-700 shrink-0">{log.ts}</span>
                <span className={`shrink-0 font-black ${LOG_COLORS[log.level]}`}>
                  {LOG_PREFIXES[log.level]}
                </span>
                <span className={LOG_COLORS[log.level]}>{log.msg}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
