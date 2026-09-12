import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from './services/api';
import { MeshVisualizer } from './components/MeshVisualizer';
import { SecureMessaging } from './components/SecureMessaging';
import { AttackSimulation } from './components/AttackSimulation';
import { DeliveryResilience } from './components/DeliveryResilience';
import { Sidebar, NavTabId } from './components/layout/Sidebar';
import { Navbar } from './components/layout/Navbar';
import { SectionHeader } from './components/layout/SectionHeader';
import { KPICard } from './components/dashboard/KPICard';
import { SystemStatusBar } from './components/dashboard/SystemStatusBar';
import {
  ConnectionState,
  RescueMember,
  HealthResponse,
  SystemInfoResponse,
  MeshTopologyResponse,
} from './types';
import {
  Users,
  KeyRound,
  UserPlus,
  CheckCircle2,
  AlertTriangle,
  Activity,
  MessageSquare,
  Package,
  Shield,
  ShieldCheck,
  WifiOff,
  Lock,
  Radio,
  Network,
} from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTabId>('overview');
  const [sidebarPinned, setSidebarPinned] = useState<boolean>(false);

  const [connectionState, setConnectionState] = useState<ConnectionState>('loading');
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [_systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastPingTime, setLastPingTime] = useState<string | null>(null);
  const [topology, setTopology] = useState<MeshTopologyResponse>({ nodes: [], edges: [] });

  const [members, setMembers] = useState<RescueMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState<boolean>(false);
  const [regName, setRegName] = useState<string>('');
  const [regTeam, setRegTeam] = useState<string>('');
  const [regRole, setRegRole] = useState<string>('');
  const [submittingReg, setSubmittingReg] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [provisioningId, setProvisioningId] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const checkBackendHealth = useCallback(async () => {
    setConnectionState('loading');
    setErrorMessage(null);
    try {
      const [health, system, topo] = await Promise.all([
        apiService.getHealth(),
        apiService.getSystemInfo(),
        apiService.fetchMeshTopology().catch(() => ({ nodes: [], edges: [] })),
      ]);
      setHealthData(health);
      setSystemInfo(system);
      setTopology(topo);
      setConnectionState('connected');
      setLastPingTime(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setConnectionState('error');
      setHealthData(null);
      setSystemInfo(null);
      if (err instanceof Error) setErrorMessage(err.message);
      else setErrorMessage('Failed to connect to backend service.');
      setLastPingTime(new Date().toLocaleTimeString());
    }
  }, []);

  const loadMembers = useCallback(async () => {
    setLoadingMembers(true);
    try {
      const data = await apiService.fetchMembers();
      setMembers(data);
    } catch {
      // preserve state
    } finally {
      setLoadingMembers(false);
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await Promise.all([checkBackendHealth(), loadMembers()]);
    setIsRefreshing(false);
  }, [checkBackendHealth, loadMembers]);

  useEffect(() => {
    checkBackendHealth();
    loadMembers();
  }, [checkBackendHealth, loadMembers]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);
    const trimmedName = regName.trim();
    const trimmedTeam = regTeam.trim();
    const trimmedRole = regRole.trim();
    if (!trimmedName || !trimmedTeam || !trimmedRole) {
      setFormError('All fields (Name, Team, Role) are required.');
      return;
    }
    setSubmittingReg(true);
    try {
      const newMember = await apiService.registerMember({ name: trimmedName, team: trimmedTeam, role: trimmedRole });
      setMembers((prev) => [...prev, newMember]);
      setFormSuccess(`Successfully enrolled ${newMember.name} as ${newMember.rescue_id}.`);
      setRegName(''); setRegTeam(''); setRegRole('');
      setTimeout(() => setFormSuccess(null), 4000);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setSubmittingReg(false);
    }
  };

  const handleRevoke = async (member: RescueMember) => {
    if (!window.confirm(`Deactivate access for ${member.name} (${member.rescue_id})?`)) return;
    setRevokingId(member.rescue_id);
    try {
      const updated = await apiService.revokeMember(member.rescue_id);
      setMembers((prev) => prev.map((m) => m.rescue_id === updated.rescue_id ? { ...m, status: updated.status } : m));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Revocation failed.');
    } finally {
      setRevokingId(null);
    }
  };

  const handleProvisionKeys = async (member: RescueMember) => {
    setProvisioningId(member.device_id);
    try {
      await apiService.initializeDeviceKeys(member.device_id);
      await loadMembers();
      setFormSuccess(`Keys provisioned for ${member.name} (${member.device_id}).`);
      setTimeout(() => setFormSuccess(null), 4000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Key provisioning failed.');
    } finally {
      setProvisioningId(null);
    }
  };

  const activeCount = members.filter((m) => m.status === 'active').length;
  const cryptoInitializedCount = members.filter((m) => m.signing_public_key && m.encryption_public_key).length;
  const revokedCount = members.filter((m) => m.status === 'revoked').length;
  const isConnected = connectionState === 'connected';
  return (
    <div className="flex h-screen overflow-hidden bg-[#070b13] text-slate-100 font-sans select-none">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} onPinnedChange={setSidebarPinned} />

      <div className={`flex flex-col flex-1 min-w-0 overflow-hidden transition-[padding] duration-300 ${sidebarPinned ? 'pl-64' : 'pl-[4.5rem]'}`}>
        <Navbar
          activeTab={activeTab}
          isConnected={isConnected}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing || connectionState === 'loading'}
        />

        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 sm:py-7 md:px-8 md:py-8 relative bg-radial from-[#0d1527] to-[#070b13]">
          <div className="absolute top-[15%] right-[5%] w-[450px] h-[450px] rounded-full bg-indigo-500/5 blur-[120px] pointer-events-none" />
          <div className="absolute bottom-[10%] left-[10%] w-[350px] h-[350px] rounded-full bg-violet-500/5 blur-[100px] pointer-events-none" />

          <div className="max-w-7xl mx-auto space-y-6 relative">
            {/* Connection Error Banner */}
            {connectionState === 'error' && (
              <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl p-4">
                <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                <div className="text-xs">
                  <strong className="font-bold">Backend unreachable.</strong> {errorMessage}
                  <br />
                  <span className="text-red-500/70">Make sure the backend is running: <code className="font-mono">uvicorn backend.app.main:app --port 8000</code></span>
                </div>
              </div>
            )}

            {/* ─── OVERVIEW ─── */}
            {activeTab === 'overview' && (
              <div className="space-y-6 animate-fade-in">
                {/* Hero explanation */}
                <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                      <Radio className="w-5 h-5 text-indigo-400" />
                    </div>
                    <h2 className="text-lg font-black text-slate-100">What is RESQ?</h2>
                  </div>
                  <p className="text-sm text-slate-400 leading-relaxed max-w-3xl">
                    RESQ helps emergency messages travel through a <strong className="text-slate-200">local device network</strong> when normal communication infrastructure is unavailable.
                    When cellular networks fail during a disaster, RESQ routes encrypted messages through nearby rescue devices in a peer-to-peer mesh — without relying on the internet.
                  </p>
                </div>

                {/* KPIs */}
                <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <KPICard
                    title="Mesh Nodes"
                    value={topology.nodes.length || '—'}
                    subtitle="Active relay devices"
                    icon={Network}
                    accentColor="cyan"
                    loading={connectionState === 'loading' && !healthData}
                  />
                  <KPICard
                    title="Active Responders"
                    value={activeCount || members.length}
                    subtitle={`${cryptoInitializedCount} with keys • ${revokedCount} revoked`}
                    icon={Users}
                    accentColor="green"
                    loading={loadingMembers && members.length === 0}
                  />
                  <KPICard
                    title="Network Links"
                    value={topology.edges.length || '—'}
                    subtitle="Multi-hop mesh paths"
                    icon={Radio}
                    accentColor="indigo"
                    loading={connectionState === 'loading' && !healthData}
                  />
                  <KPICard
                    title="Encryption"
                    value="Active"
                    subtitle="ChaCha20-Poly1305 + Ed25519"
                    icon={ShieldCheck}
                    accentColor="amber"
                    loading={connectionState === 'loading' && !healthData}
                  />
                </section>

                <SystemStatusBar
                  nodeCount={topology.nodes.length || 5}
                  edgeCount={topology.edges.length || 6}
                  isBackendConnected={isConnected}
                  lastPingTime={lastPingTime}
                  deliveredPacketsCount={activeCount}
                />

                {/* System status grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-5">
                    <div className="flex items-center gap-2 mb-3">
                      {isConnected
                        ? <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        : <span className="w-2 h-2 rounded-full bg-red-400" />}
                      <span className="text-xs font-bold text-slate-300">Backend Service</span>
                    </div>
                    <p className="text-xl font-black text-slate-100">{isConnected ? 'Online' : 'Offline'}</p>
                    <p className="text-xs text-slate-500 mt-1">{lastPingTime ? `Last checked ${lastPingTime}` : 'Connecting...'}</p>
                  </div>

                  <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <WifiOff className="w-4 h-4 text-red-400" />
                      <span className="text-xs font-bold text-red-400">Cellular Network</span>
                    </div>
                    <p className="text-xl font-black text-red-300">Unavailable</p>
                    <p className="text-xs text-slate-500 mt-1">Simulated blackout — mesh routing active</p>
                  </div>

                  <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <Lock className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-bold text-emerald-400">End-to-End Encryption</span>
                    </div>
                    <p className="text-xl font-black text-emerald-300">Enforced</p>
                    <p className="text-xs text-slate-500 mt-1">All messages encrypted before transmission</p>
                  </div>
                </div>

                {/* Quick nav cards */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {[
                    { tab: 'messages' as NavTabId, icon: MessageSquare, label: 'Emergency Messages', color: 'indigo' },
                    { tab: 'network' as NavTabId, icon: Network, label: 'Mesh Network', color: 'cyan' },
                    { tab: 'security' as NavTabId, icon: Shield, label: 'Security & Auth', color: 'emerald' },
                    { tab: 'delivery' as NavTabId, icon: Activity, label: 'Message Delivery', color: 'violet' },
                    { tab: 'packet-protection' as NavTabId, icon: Package, label: 'Packet Protection', color: 'amber' },
                  ].map(({ tab, icon: Icon, label, color }) => (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => setActiveTab(tab)}
                      className={`rounded-2xl border border-${color}-500/20 bg-${color}-500/5 hover:bg-${color}-500/10 p-4 text-left transition-all cursor-pointer group`}
                    >
                      <Icon className={`w-5 h-5 text-${color}-400 mb-2.5`} />
                      <p className="text-xs font-bold text-slate-300 group-hover:text-slate-100">{label}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* ─── EMERGENCY MESSAGES ─── */}
            {activeTab === 'messages' && (
              <div className="space-y-6 animate-fade-in">
                <div className="flex items-center gap-3 border-b border-slate-800/70 pb-5">
                  <div className="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20">
                    <MessageSquare className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-black text-slate-100">Emergency Messages</h2>
                    <p className="text-xs text-slate-400 mt-0.5">Compose, send, and track encrypted emergency messages through the mesh network.</p>
                  </div>
                </div>
                <SecureMessaging members={members} onRefreshMembers={loadMembers} />
              </div>
            )}

            {/* ─── NETWORK ─── */}
            {activeTab === 'network' && (
              <div className="space-y-6 animate-fade-in">
                <div className="flex items-center gap-3 border-b border-slate-800/70 pb-5">
                  <div className="p-2.5 rounded-2xl bg-cyan-500/10 border border-cyan-500/20">
                    <Network className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-black text-slate-100">Mesh Network</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Visualize the peer-to-peer relay network. Simulate node failures, connection outages, and alternative route discovery.
                    </p>
                  </div>
                </div>
                <MeshVisualizer />
              </div>
            )}

            {/* ─── SECURITY ─── */}
            {activeTab === 'security' && (
              <div className="space-y-6 animate-fade-in">
                <div className="flex items-center gap-3 border-b border-slate-800/70 pb-5">
                  <div className="p-2.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
                    <Shield className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-black text-slate-100">Security &amp; Authorization</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Every message is verified, signed, and authorized before decryption is allowed. No plaintext is ever exposed to intermediate nodes.
                    </p>
                  </div>
                </div>

                {/* Security principle cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    {
                      icon: CheckCircle2,
                      color: 'emerald',
                      title: 'Sender Verified',
                      desc: 'The sender must be a registered, active rescue responder. Revoked or unknown senders are immediately rejected.',
                    },
                    {
                      icon: Lock,
                      color: 'indigo',
                      title: 'Message Protected',
                      desc: 'Messages are encrypted with X25519 key agreement and ChaCha20-Poly1305 authenticated encryption before leaving the device.',
                    },
                    {
                      icon: ShieldCheck,
                      color: 'cyan',
                      title: 'Signature Verified',
                      desc: 'Every packet is signed with Ed25519. Any modification to the packet in transit causes signature verification to fail.',
                    },
                    {
                      icon: Users,
                      color: 'amber',
                      title: 'Recipient Authorized',
                      desc: 'Only the intended, active recipient can pass the decryption gate. Wrong recipient, wrong key, or modified packet — all rejected.',
                    },
                  ].map(({ icon: Icon, color, title, desc }) => (
                    <div key={title} className={`rounded-2xl border border-${color}-500/20 bg-${color}-500/5 p-5`}>
                      <div className="flex items-center gap-3 mb-3">
                        <Icon className={`w-5 h-5 text-${color}-400`} />
                        <h3 className={`font-bold text-${color}-300 text-sm`}>{title}</h3>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">{desc}</p>
                    </div>
                  ))}
                </div>

                {/* Verification flow */}
                <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-6">
                  <h3 className="text-sm font-bold text-slate-200 mb-4">Message Authorization Flow</h3>
                  <div className="space-y-2">
                    {[
                      'Registry lookup — sender must exist',
                      'Active status check — sender must not be revoked',
                      'Ed25519 signature verification — packet integrity confirmed',
                      'Recipient authorization — only intended device proceeds',
                      'Authenticated decryption — ChaCha20-Poly1305 decryption with integrity check',
                      'Plaintext released — only after all checks pass',
                    ].map((step, i) => (
                      <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-800/40 last:border-0">
                        <span className="w-6 h-6 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                        <span className="text-xs text-slate-300">{step}</span>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 ml-auto shrink-0" />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Technical details section */}
                <div className="rounded-2xl border border-slate-800/60 bg-slate-900/20 p-6">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Technical Details</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { label: 'Key Agreement', value: 'X25519 ECDH' },
                      { label: 'Key Derivation', value: 'HKDF-SHA256' },
                      { label: 'Encryption', value: 'ChaCha20-Poly1305' },
                      { label: 'Digital Signature', value: 'Ed25519' },
                    ].map(({ label, value }) => (
                      <div key={label} className="text-center">
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{label}</p>
                        <p className="text-xs font-mono font-bold text-indigo-300">{value}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ─── MESSAGE DELIVERY ─── */}
            {activeTab === 'delivery' && (
              <DeliveryResilience members={members} onNavigateToMessages={() => setActiveTab('messages')} />
            )}

            {/* ─── PACKET PROTECTION ─── */}
            {activeTab === 'packet-protection' && (
              <div className="space-y-6 animate-fade-in">
                <div className="flex items-center gap-3 border-b border-slate-800/70 pb-5">
                  <div className="p-2.5 rounded-2xl bg-amber-500/10 border border-amber-500/20">
                    <Package className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-black text-slate-100">Packet Protection Demo</h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      See what an attacker sees when they capture a packet — and why encryption makes the difference.
                    </p>
                  </div>
                </div>

                {/* Key explanation */}
                <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5">
                  <p className="text-sm text-amber-200 font-semibold mb-1">The goal is not to prevent packet capture.</p>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    The goal is to ensure that <strong className="text-slate-200">capturing a packet does not reveal the emergency message</strong>.
                    An attacker on the same network may always intercept packets.
                    Encryption means those packets are meaningless without the recipient's private key.
                  </p>
                </div>

                {/* Side-by-side comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-5">
                    <h3 className="text-sm font-bold text-red-300 mb-4 flex items-center gap-2">
                      <WifiOff className="w-4 h-4" /> Unprotected Communication
                    </h3>
                    <div className="space-y-3 text-xs">
                      <div className="flex items-center gap-2 text-slate-400">
                        <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold flex items-center justify-center">1</span>
                        Message composed in plaintext
                      </div>
                      <div className="flex items-center gap-2 text-slate-400">
                        <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold flex items-center justify-center">2</span>
                        Unencrypted packet transmitted
                      </div>
                      <div className="flex items-center gap-2 text-red-400">
                        <span className="w-6 h-6 rounded-full bg-red-500/20 text-red-400 text-[10px] font-bold flex items-center justify-center">3</span>
                        Attacker captures packet
                      </div>
                      <div className="flex items-center gap-2 text-red-400 font-bold">
                        <span className="w-6 h-6 rounded-full bg-red-500/20 text-red-400 text-[10px] font-bold flex items-center justify-center">4</span>
                        Attacker reads original message ⚠️
                      </div>
                    </div>
                    <div className="mt-4 p-3 bg-red-900/20 border border-red-500/20 rounded-xl font-mono text-xs text-red-300">
                      "SOS: Three trapped in building B. Send medics immediately."
                    </div>
                    <p className="text-[10px] text-red-400 font-bold mt-2 uppercase tracking-wider">Result: Message exposed</p>
                  </div>

                  <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-5">
                    <h3 className="text-sm font-bold text-emerald-300 mb-4 flex items-center gap-2">
                      <Lock className="w-4 h-4" /> Protected Communication
                    </h3>
                    <div className="space-y-3 text-xs">
                      <div className="flex items-center gap-2 text-slate-400">
                        <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold flex items-center justify-center">1</span>
                        Message encrypted with recipient's key
                      </div>
                      <div className="flex items-center gap-2 text-slate-400">
                        <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold flex items-center justify-center">2</span>
                        Encrypted + signed packet transmitted
                      </div>
                      <div className="flex items-center gap-2 text-slate-400">
                        <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold flex items-center justify-center">3</span>
                        Attacker captures packet
                      </div>
                      <div className="flex items-center gap-2 text-emerald-400 font-bold">
                        <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold flex items-center justify-center">4</span>
                        Attacker sees only ciphertext ✓
                      </div>
                    </div>
                    <div className="mt-4 p-3 bg-emerald-900/10 border border-emerald-500/20 rounded-xl font-mono text-xs text-slate-500 break-all">
                      ChaCha20ciphertext+Poly1305tag...nonce+salt+ephemeralkey+Ed25519sig
                    </div>
                    <p className="text-[10px] text-emerald-400 font-bold mt-2 uppercase tracking-wider">Result: Message protected — only authorized recipient can read</p>
                  </div>
                </div>

                {/* Live demo via AttackSimulation */}
                <div className="rounded-2xl border border-slate-800/60 bg-slate-900/20 p-4">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Live Demonstration</h3>
                  <AttackSimulation />
                </div>
              </div>
            )}

            {/* ─── DEVICE REGISTRY ─── */}
            {activeTab === 'registry' && (
              <div className="space-y-8 animate-fade-in">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/70 pb-5">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20">
                      <KeyRound className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div>
                      <h2 className="text-xl font-black text-slate-100">Device Registry</h2>
                      <p className="text-xs text-slate-400 mt-0.5">Register rescue responders and manage their cryptographic device identities.</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={loadMembers}
                    disabled={loadingMembers}
                    className="px-4 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-slate-100 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1.5 self-start sm:self-auto"
                  >
                    <Activity className="w-3.5 h-3.5 text-indigo-400" />
                    {loadingMembers ? 'Syncing...' : 'Sync Registry'}
                  </button>
                </div>

                {formSuccess && (
                  <div className="flex items-center gap-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl p-3.5 text-xs">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>{formSuccess}</span>
                  </div>
                )}
                {formError && (
                  <div className="flex items-center gap-2.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl p-3.5 text-xs">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{formError}</span>
                  </div>
                )}

                <div className="glass-card rounded-2xl border border-slate-800/60 p-6">
                  <SectionHeader
                    title="Enroll Emergency Responder"
                    accentColor="bg-indigo-500"
                    subtitle="Auto-generates a unique Rescue ID and Device ID with cryptographic keys."
                  />
                  <form onSubmit={handleRegister} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Responder Name</label>
                        <input
                          type="text"
                          placeholder="e.g. Maya Chen"
                          value={regName}
                          onChange={(e) => setRegName(e.target.value)}
                          disabled={submittingReg}
                          className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 outline-none focus:border-indigo-500 font-medium"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Team / Unit</label>
                        <input
                          type="text"
                          placeholder="e.g. Search &amp; Rescue Alpha"
                          value={regTeam}
                          onChange={(e) => setRegTeam(e.target.value)}
                          disabled={submittingReg}
                          className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 outline-none focus:border-indigo-500 font-medium"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Role</label>
                        <input
                          type="text"
                          placeholder="e.g. Field Medic"
                          value={regRole}
                          onChange={(e) => setRegRole(e.target.value)}
                          disabled={submittingReg}
                          className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 outline-none focus:border-indigo-500 font-medium"
                        />
                      </div>
                    </div>
                    <div className="flex justify-end pt-2">
                      <button
                        type="submit"
                        disabled={submittingReg}
                        className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white rounded-xl text-xs font-black uppercase tracking-wider shadow-lg shadow-indigo-600/15 transition-all cursor-pointer flex items-center gap-2 disabled:opacity-50"
                      >
                        <UserPlus className="w-4 h-4" />
                        {submittingReg ? 'Enrolling...' : 'Enroll Responder'}
                      </button>
                    </div>
                  </form>
                </div>

                <div className="glass-card rounded-2xl border border-slate-800/60 p-6 overflow-hidden">
                  <SectionHeader title="Registered Responders" accentColor="bg-cyan-500" />
                  {loadingMembers && members.length === 0 ? (
                    <div className="py-12 text-center text-slate-500 font-mono text-xs animate-pulse">Loading registry...</div>
                  ) : members.length === 0 ? (
                    <div className="py-12 text-center text-slate-500 space-y-2">
                      <Users className="w-8 h-8 mx-auto text-slate-600" />
                      <p className="text-xs">No rescue responders enrolled yet.</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto border border-slate-900 rounded-xl">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead className="bg-slate-900/80 border-b border-slate-800">
                          <tr>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Rescue ID</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Device ID</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Name</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Team</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Role</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Status</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Keys</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/40 font-mono">
                          {members.map((member) => {
                            const hasKeys = !!(member.signing_public_key && member.encryption_public_key);
                            const isRevoked = member.status === 'revoked';
                            return (
                              <tr key={member.rescue_id} className="hover:bg-slate-850/40">
                                <td className="px-4 py-3 font-bold text-indigo-400">{member.rescue_id}</td>
                                <td className="px-4 py-3 text-slate-300">{member.device_id}</td>
                                <td className="px-4 py-3 font-sans font-bold text-slate-100">{member.name}</td>
                                <td className="px-4 py-3 font-sans text-slate-400">{member.team}</td>
                                <td className="px-4 py-3 font-sans">
                                  <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300 font-semibold uppercase">{member.role}</span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${isRevoked ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'}`}>
                                    {isRevoked ? 'Revoked' : 'Active'}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${hasKeys ? 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400' : 'bg-amber-500/10 border-amber-500/20 text-amber-400'}`}>
                                    {hasKeys ? 'Provisioned' : 'No Keys'}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <div className="flex items-center justify-end gap-2">
                                    {!hasKeys && !isRevoked && (
                                      <button
                                        type="button"
                                        onClick={() => handleProvisionKeys(member)}
                                        disabled={provisioningId === member.device_id}
                                        className="px-2.5 py-1 bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50"
                                      >
                                        {provisioningId === member.device_id ? 'Generating...' : 'Generate Keys'}
                                      </button>
                                    )}
                                    {!isRevoked ? (
                                      <button
                                        type="button"
                                        onClick={() => handleRevoke(member)}
                                        disabled={revokingId === member.rescue_id}
                                        className="px-2.5 py-1 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50"
                                      >
                                        {revokingId === member.rescue_id ? 'Revoking...' : 'Revoke'}
                                      </button>
                                    ) : (
                                      <span className="text-[10px] text-slate-600 font-bold uppercase">Deactivated</span>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;
