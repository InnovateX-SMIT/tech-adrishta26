import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from './services/api';
import { MeshVisualizer } from './components/MeshVisualizer';
import { SecureMessaging } from './components/SecureMessaging';
import { AttackSimulation } from './components/AttackSimulation';
import { Sidebar, NavTabId } from './components/layout/Sidebar';
import { Navbar } from './components/layout/Navbar';
import { SectionHeader } from './components/layout/SectionHeader';
import {
  ConnectionState,
  RescueMember,
} from './types';
import {
  Users,
  KeyRound,
  UserPlus,
  CheckCircle2,
  AlertTriangle,
  Activity,
} from 'lucide-react';

export const App: React.FC = () => {
  // Navigation & Shell state
  const [activeTab, setActiveTab] = useState<NavTabId>('mesh');
  const [sidebarPinned, setSidebarPinned] = useState<boolean>(false);

  // Backend status states
  const [connectionState, setConnectionState] = useState<ConnectionState>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Registry states
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

  const checkBackendHealth = useCallback(async () => {
    setConnectionState('loading');
    setErrorMessage(null);

    try {
      await apiService.getHealth();
      setConnectionState('connected');
    } catch (err: unknown) {
      setConnectionState('error');
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to connect to backend service.');
      }
    }
  }, []);

  const loadMembers = useCallback(async () => {
    setLoadingMembers(true);
    try {
      const data = await apiService.fetchMembers();
      setMembers(data);
    } catch {
      // Backend down, preserve local empty state
    } finally {
      setLoadingMembers(false);
    }
  }, []);

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
      const newMember = await apiService.registerMember({
        name: trimmedName,
        team: trimmedTeam,
        role: trimmedRole,
      });

      setMembers((prev) => [...prev, newMember]);
      setFormSuccess(`Successfully enrolled ${newMember.name} as ${newMember.rescue_id}.`);
      setRegName('');
      setRegTeam('');
      setRegRole('');
      setTimeout(() => setFormSuccess(null), 4000);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Registration failed.');
      }
    } finally {
      setSubmittingReg(false);
    }
  };

  const handleRevoke = async (member: RescueMember) => {
    if (!window.confirm(`Deactivate access for responder ${member.name} (${member.rescue_id})?`)) {
      return;
    }

    setRevokingId(member.rescue_id);
    try {
      const updated = await apiService.revokeMember(member.rescue_id);
      setMembers((prev) =>
        prev.map((m) => (m.rescue_id === updated.rescue_id ? { ...m, status: updated.status } : m))
      );
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

  return (
    <div className="flex h-screen overflow-hidden bg-[#070b13] text-slate-100 font-sans select-none">
      {/* 1. Fixed Collapsible Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onPinnedChange={setSidebarPinned}
      />

      {/* 2. Main Viewport Container */}
      <div
        className={`flex flex-col flex-1 min-w-0 overflow-hidden transition-[padding] duration-300 ${
          sidebarPinned ? 'pl-64' : 'pl-[4.5rem]'
        }`}
      >
        {/* Sticky Top Navbar */}
        <Navbar
          activeTab={activeTab}
          isConnected={connectionState === 'connected'}
          onRefresh={() => {
            checkBackendHealth();
            loadMembers();
          }}
          isRefreshing={connectionState === 'loading'}
        />

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 sm:py-7 md:px-8 md:py-8 relative bg-radial from-[#0d1527] to-[#070b13] animate-fade-in">
          {/* Ambient Lighting Orbs */}
          <div className="absolute top-[15%] right-[5%] w-[450px] h-[450px] rounded-full bg-indigo-500/5 blur-[120px] pointer-events-none" />
          <div className="absolute bottom-[10%] left-[10%] w-[350px] h-[350px] rounded-full bg-violet-500/5 blur-[100px] pointer-events-none" />

          <div className="max-w-7xl mx-auto space-y-6 relative">

            {/* Connection Error Banner */}
            {connectionState === 'error' && (
              <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl p-4 animate-shake">
                <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
                <div className="text-xs">
                  <strong className="uppercase tracking-wider">Backend Unreachable:</strong> {errorMessage} (Ensure `uvicorn backend.app.main:app --port 8000` is running).
                </div>
              </div>
            )}

            {/* TAB 1: MESH SIMULATION */}
            {activeTab === 'mesh' && (
              <div className="space-y-6">
                <MeshVisualizer />
              </div>
            )}

            {/* TAB 2: SECURE TRANSMIT */}
            {activeTab === 'messages' && (
              <div className="space-y-6">
                <SecureMessaging members={members} onRefreshMembers={loadMembers} />
              </div>
            )}

            {/* TAB 3: ATTACK SIMULATION & CONTRAST MODE (PHASE 7) */}
            {activeTab === 'attack' && (
              <div className="space-y-6">
                <AttackSimulation />
              </div>
            )}

            {/* TAB 4: RESCUE REGISTRY & IDENTITY */}
            {activeTab === 'registry' && (
              <div className="space-y-8 animate-fade-in">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/70 pb-5">
                  <div>
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                        <KeyRound className="w-5 h-5" />
                      </div>
                      <div>
                        <h1 className="text-xl sm:text-2xl font-black text-slate-100 uppercase tracking-tight">
                          Trusted Rescue-Team Registry
                        </h1>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Cryptographic identity authority, key management, and responder hardware authorization.
                        </p>
                      </div>
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

                {/* Notifications */}
                {formSuccess && (
                  <div className="flex items-center gap-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl p-3.5 text-xs animate-fade-in">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>{formSuccess}</span>
                  </div>
                )}
                {formError && (
                  <div className="flex items-center gap-2.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl p-3.5 text-xs animate-shake">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{formError}</span>
                  </div>
                )}

                {/* Registration Form Card */}
                <div className="glass-card rounded-2xl border border-slate-800/60 p-6">
                  <SectionHeader
                    title="Enroll Emergency Responder & Provision Device"
                    accentColor="bg-indigo-500"
                    subtitle="Auto-generates verified RESQ-### identifier and hardware DEVICE-### certificate."
                  />

                  <form onSubmit={handleRegister} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                          Responder Name
                        </label>
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
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                          Tactical Team / Unit
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. Search & Rescue Alpha"
                          value={regTeam}
                          onChange={(e) => setRegTeam(e.target.value)}
                          disabled={submittingReg}
                          className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 outline-none focus:border-indigo-500 font-medium"
                        />
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                          Operational Role
                        </label>
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
                        {submittingReg ? 'Enrolling Unit...' : 'Enroll Responder'}
                      </button>
                    </div>
                  </form>
                </div>

                {/* Members Table Card */}
                <div className="glass-card rounded-2xl border border-slate-800/60 p-6 overflow-hidden">
                  <SectionHeader
                    title="Authorized Responders & Cryptographic Identity Table"
                    accentColor="bg-cyan-500"
                  />

                  {loadingMembers && members.length === 0 ? (
                    <div className="py-12 text-center text-slate-500 font-mono text-xs animate-pulse">
                      Loading registry cryptographic database...
                    </div>
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
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Tactical Unit</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Role</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Status</th>
                            <th className="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Key Status</th>
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
                                  <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300 font-semibold uppercase">
                                    {member.role}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  <span
                                    className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${
                                      member.status === 'active'
                                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                        : 'bg-red-500/10 border-red-500/20 text-red-400'
                                    }`}
                                  >
                                    {member.status.toUpperCase()}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  {hasKeys ? (
                                    <span className="px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                                      PROVISIONED
                                    </span>
                                  ) : (
                                    <span className="px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider bg-amber-500/10 border border-amber-500/20 text-amber-400">
                                      UNINITIALIZED
                                    </span>
                                  )}
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
