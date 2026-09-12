import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from './services/api';
import { MeshVisualizer } from './components/MeshVisualizer';
import { SecureMessaging } from './components/SecureMessaging';
import {
  HealthResponse,
  SystemInfoResponse,
  ConnectionState,
  RescueMember,
} from './types';

export const App: React.FC = () => {
  // Navigation state
  const [activeTab, setActiveTab] = useState<'mesh' | 'messages' | 'registry' | 'roadmap'>('mesh');

  // Backend status states
  const [connectionState, setConnectionState] = useState<ConnectionState>('loading');
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastPingTime, setLastPingTime] = useState<string | null>(null);

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
      const [health, system] = await Promise.all([
        apiService.getHealth(),
        apiService.getSystemInfo(),
      ]);

      setHealthData(health);
      setSystemInfo(system);
      setConnectionState('connected');
      setLastPingTime(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setConnectionState('error');
      setHealthData(null);
      setSystemInfo(null);
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to connect to backend service.');
      }
      setLastPingTime(new Date().toLocaleTimeString());
    }
  }, []);

  const loadMembers = useCallback(async () => {
    setLoadingMembers(true);
    try {
      const data = await apiService.fetchMembers();
      setMembers(data);
    } catch {
      // If backend is down, members stay empty
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
      setFormError('All fields (Name, Team, Role) are required and cannot be whitespace-only.');
      return;
    }

    setSubmittingReg(true);
    try {
      const newMember = await apiService.registerMember({
        name: trimmedName,
        team: trimmedTeam,
        role: trimmedRole,
      });

      setFormSuccess(`Registered ${newMember.name} with ID ${newMember.rescue_id} (${newMember.device_id}).`);
      setRegName('');
      setRegTeam('');
      setRegRole('');
      await loadMembers();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Failed to register member.');
      }
    } finally {
      setSubmittingReg(false);
    }
  };

  const handleRevoke = async (member: RescueMember) => {
    const confirmed = window.confirm(
      `Confirm Revocation:\n\nAre you sure you want to revoke ${member.name} (${member.rescue_id})?\n\nThis will mark the device inactive in the registry while preserving the historical record.`
    );
    if (!confirmed) return;

    setRevokingId(member.rescue_id);
    setFormError(null);
    setFormSuccess(null);

    try {
      await apiService.revokeMember(member.rescue_id);
      setFormSuccess(`Revoked member ${member.rescue_id} (${member.name}). Record preserved as inactive.`);
      await loadMembers();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(`Revocation failed: ${err.message}`);
      } else {
        setFormError('Revocation failed.');
      }
    } finally {
      setRevokingId(null);
    }
  };

  const handleProvisionKeys = async (member: RescueMember) => {
    setProvisioningId(member.device_id);
    setFormError(null);
    setFormSuccess(null);

    try {
      const result = await apiService.initializeDeviceKeys(member.device_id);
      setFormSuccess(
        `Provisioned keys for ${member.name} (${result.device_id}): Ed25519 signing and X25519 key-agreement initialized.`
      );
      await loadMembers();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(`Key provisioning failed: ${err.message}`);
      } else {
        setFormError('Key provisioning failed.');
      }
    } finally {
      setProvisioningId(null);
    }
  };

  const activeCount = members.filter((m) => m.status === 'active').length;
  const revokedCount = members.filter((m) => m.status === 'revoked').length;
  const cryptoInitializedCount = members.filter(
    (m) => m.signing_public_key && m.encryption_public_key
  ).length;

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <div className="brand-section">
          <div className="logo-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z" />
              <path d="M12 8v4m0 4h.01" />
            </svg>
          </div>
          <div>
            <h1 className="brand-title">RESQ</h1>
            <p className="brand-subtitle">Secure Emergency Mesh Communication</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span className="phase-tag" style={{ background: 'rgba(16, 185, 129, 0.2)', color: 'var(--accent-emerald)', border: '1px solid var(--accent-emerald)' }}>
            Phase 6: End-to-End Secure Transmission Active
          </span>
          <button
            id="refresh-status-btn"
            className="btn-refresh"
            onClick={() => {
              checkBackendHealth();
              loadMembers();
            }}
            disabled={connectionState === 'loading'}
          >
            <span className={connectionState === 'loading' ? 'dot pulse' : 'dot'} />
            {connectionState === 'loading' ? 'Checking API...' : 'Ping Backend'}
          </button>
        </div>
      </header>

      {/* Hero Problem Statement */}
      <section className="hero-card">
        <div className="hero-badge">
          <span>🔒 Cryptographic Mesh Security Active</span>
        </div>
        <h2 className="hero-title">
          End-to-end authenticated, encrypted emergency mesh communication across blackout zones.
        </h2>
        <p className="hero-description">
          Phase 6 integrates the entire emergency pipeline: X25519 key agreement, HKDF-SHA256 derivation,
          ChaCha20-Poly1305 AEAD payload encryption, Ed25519 canonical JSON signatures, multi-hop mesh routing,
          and a strict 6-step recipient authorization gate protecting emergency dispatches from passive sniffing,
          tampering, and replay attacks.
        </p>
      </section>

      {/* Navigation Tabs */}
      <div className="tab-nav">
        <button
          id="tab-mesh-btn"
          className={`tab-btn ${activeTab === 'mesh' ? 'active' : ''}`}
          onClick={() => setActiveTab('mesh')}
        >
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" strokeWidth="2">
            <circle cx="6" cy="6" r="3" />
            <circle cx="18" cy="6" r="3" />
            <circle cx="12" cy="18" r="3" />
            <path d="M8.5 7.5l7 0M7.5 8.5l3.5 7M16.5 8.5l-3.5 7" />
          </svg>
          Mesh Topology &amp; Simulation
        </button>
        <button
          id="tab-messages-btn"
          className={`tab-btn ${activeTab === 'messages' ? 'active' : ''}`}
          onClick={() => setActiveTab('messages')}
        >
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          Secure Messaging &amp; Gate (Phase 6)
        </button>
        <button
          id="tab-registry-btn"
          className={`tab-btn ${activeTab === 'registry' ? 'active' : ''}`}
          onClick={() => setActiveTab('registry')}
        >
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" strokeWidth="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          Rescue Registry &amp; Cryptographic Keys
        </button>
        <button
          id="tab-roadmap-btn"
          className={`tab-btn ${activeTab === 'roadmap' ? 'active' : ''}`}
          onClick={() => setActiveTab('roadmap')}
        >
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
          10-Phase Roadmap
        </button>
      </div>

      {/* TAB 1: Mesh Visualizer */}
      {activeTab === 'mesh' && (
        <section style={{ marginTop: '1rem' }}>
          <MeshVisualizer />
        </section>
      )}

      {/* TAB 2: Secure Messaging & Controlled Decryption Gate */}
      {activeTab === 'messages' && (
        <section style={{ marginTop: '1rem' }}>
          <SecureMessaging members={members} onRefreshMembers={loadMembers} />
        </section>
      )}

      {/* TAB 2: Registry & Cryptographic Keys */}
      {activeTab === 'registry' && (
        <>
          {/* Backend Infrastructure Status Grid */}
          <div className="grid-2" style={{ marginTop: '1.5rem' }}>
            {/* Backend Connectivity Card */}
            <div className="card" id="backend-status-card">
              <div className="card-header">
                <h3 className="card-title">
                  <span>Backend Connection</span>
                </h3>
                <span className={`status-pill ${connectionState}`}>
                  <span className={`dot ${connectionState === 'loading' ? 'pulse' : ''}`} />
                  {connectionState === 'connected' && 'CONNECTED'}
                  {connectionState === 'loading' && 'CONNECTING'}
                  {connectionState === 'error' && 'UNREACHABLE'}
                </span>
              </div>

              {connectionState === 'connected' && healthData && systemInfo ? (
                <table className="info-table">
                  <tbody>
                    <tr>
                      <td className="label-col">API Base URL</td>
                      <td className="val-col">{apiService.getBaseUrl()}</td>
                    </tr>
                    <tr>
                      <td className="label-col">Service ID</td>
                      <td className="val-col">{healthData.service}</td>
                    </tr>
                    <tr>
                      <td className="label-col">Health Status</td>
                      <td className="val-col" style={{ color: 'var(--accent-emerald)' }}>
                        {healthData.status.toUpperCase()}
                      </td>
                    </tr>
                    <tr>
                      <td className="label-col">Active Phase</td>
                      <td className="val-col">{healthData.phase}</td>
                    </tr>
                    <tr>
                      <td className="label-col">Environment</td>
                      <td className="val-col">{systemInfo.mode}</td>
                    </tr>
                    <tr>
                      <td className="label-col">Last Verified</td>
                      <td className="val-col">{lastPingTime || 'Just now'}</td>
                    </tr>
                  </tbody>
                </table>
              ) : connectionState === 'loading' ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', padding: '1.5rem 0' }}>
                  Querying backend health endpoint at <code>{apiService.getBaseUrl()}</code>...
                </p>
              ) : (
                <div>
                  <table className="info-table">
                    <tbody>
                      <tr>
                        <td className="label-col">Target URL</td>
                        <td className="val-col">{apiService.getBaseUrl()}</td>
                      </tr>
                      <tr>
                        <td className="label-col">Status</td>
                        <td className="val-col" style={{ color: 'var(--accent-rose)' }}>Connection Failed</td>
                      </tr>
                      <tr>
                        <td className="label-col">Last Attempt</td>
                        <td className="val-col">{lastPingTime}</td>
                      </tr>
                    </tbody>
                  </table>
                  <div className="notice-box error">
                    <strong>Connection Error:</strong> {errorMessage}
                  </div>
                </div>
              )}
            </div>

            {/* Security State Card */}
            <div className="card" id="security-state-card">
              <div className="card-header">
                <h3 className="card-title">
                  <span>Security State</span>
                </h3>
                <span className="status-pill active">PHASE 4 ACTIVE</span>
              </div>

              <table className="info-table">
                <tbody>
                  <tr>
                    <td className="label-col">Cryptographic Engine</td>
                    <td className="val-col" style={{ color: 'var(--accent-emerald)' }}>
                      ACTIVE (Ed25519 &amp; X25519)
                    </td>
                  </tr>
                  <tr>
                    <td className="label-col">Authenticated Cipher</td>
                    <td className="val-col" style={{ color: 'var(--accent-emerald)' }}>
                      ChaCha20-Poly1305 + HKDF-SHA256
                    </td>
                  </tr>
                  <tr>
                    <td className="label-col">Private-Key Storage</td>
                    <td className="val-col" style={{ color: 'var(--accent-cyan)' }}>
                      LOCAL (keys/&lt;device_id&gt;/ &bull; PKCS8 PEM)
                    </td>
                  </tr>
                  <tr>
                    <td className="label-col">Software Mesh Relay</td>
                    <td className="val-col" style={{ color: 'var(--accent-emerald)' }}>
                      ACTIVE (In-Memory BFS Multi-Hop)
                    </td>
                  </tr>
                  <tr>
                    <td className="label-col">Attacker Packet Sniffer</td>
                    <td className="val-col" style={{ color: 'var(--accent-amber)' }}>
                      ACTIVE (Passive Tap on NODE-B &lt;-&gt; NODE-C)
                    </td>
                  </tr>
                </tbody>
              </table>

              <div className="notice-box warning">
                <strong>Security Boundary Notice:</strong> Cryptographic key generation, digital signatures,
                and ChaCha20-Poly1305 authenticated envelopes are stored securely. Local private keys are stored on the host filesystem under
                <code>keys/&lt;device_id&gt;/</code> (development prototype) and are never exposed over APIs or transmitted across mesh hops.
              </div>
            </div>
          </div>

          {/* Phase 2 & 3: Registry & Device Identity Management Section */}
          <section style={{ marginTop: '2.5rem' }}>
            <div style={{ marginBottom: '1.25rem' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>
                Trusted Rescue-Team Registry &amp; Cryptographic Identities
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Administrative registry for authorized emergency rescue personnel, device provisioning, and cryptographic keys.
              </p>
            </div>

            {/* Metrics Grid */}
            <div className="grid-4">
              <div className="stat-box">
                <span className="stat-label">Total Responders</span>
                <span className="stat-value">{members.length}</span>
                <span className="stat-desc">Registered personnel</span>
              </div>

              <div className="stat-box">
                <span className="stat-label">Active Units</span>
                <span className="stat-value" style={{ color: 'var(--accent-emerald)' }}>{activeCount}</span>
                <span className="stat-desc">Authorized for deployment</span>
              </div>

              <div className="stat-box">
                <span className="stat-label">Key Provisioned</span>
                <span className="stat-value" style={{ color: 'var(--accent-cyan)' }}>{cryptoInitializedCount}</span>
                <span className="stat-desc">Ed25519 &amp; X25519 ready</span>
              </div>

              <div className="stat-box">
                <span className="stat-label">Revoked Units</span>
                <span className="stat-value" style={{ color: 'var(--accent-rose)' }}>{revokedCount}</span>
                <span className="stat-desc">Access suspended</span>
              </div>
            </div>

            {/* Notifications */}
            {formSuccess && (
              <div className="notice-box success" style={{ marginBottom: '1.25rem' }}>
                <strong>Success:</strong> {formSuccess}
              </div>
            )}
            {formError && (
              <div className="notice-box error" style={{ marginBottom: '1.25rem' }}>
                <strong>Error:</strong> {formError}
              </div>
            )}

            {/* Member Registration Form */}
            <div className="card" style={{ marginBottom: '2rem' }}>
              <div className="card-header">
                <h3 className="card-title">
                  <span>Register Rescue Responder</span>
                </h3>
                <span className="readiness-pill">Auto-generates RESQ-### &amp; DEVICE-###</span>
              </div>

              <form onSubmit={handleRegister}>
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label" htmlFor="responder-name">Responder Name</label>
                    <input
                      id="responder-name"
                      className="form-input"
                      type="text"
                      placeholder="e.g. Aarav Sharma"
                      value={regName}
                      onChange={(e) => setRegName(e.target.value)}
                      disabled={submittingReg}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="responder-team">Rescue Unit / Team</label>
                    <input
                      id="responder-team"
                      className="form-input"
                      type="text"
                      placeholder="e.g. Search & Rescue Alpha"
                      value={regTeam}
                      onChange={(e) => setRegTeam(e.target.value)}
                      disabled={submittingReg}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="responder-role">Tactical Role</label>
                    <input
                      id="responder-role"
                      className="form-input"
                      type="text"
                      placeholder="e.g. Incident Commander"
                      value={regRole}
                      onChange={(e) => setRegRole(e.target.value)}
                      disabled={submittingReg}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                  <button
                    id="submit-responder-btn"
                    className="btn-primary"
                    type="submit"
                    disabled={submittingReg}
                  >
                    {submittingReg ? 'Enrolling Unit...' : 'Enroll in Registry'}
                  </button>
                </div>
              </form>
            </div>

            {/* Members Table */}
            <div className="card" id="registry-table-card">
              <div className="card-header">
                <h3 className="card-title">
                  <span>Registered Emergency Devices</span>
                </h3>
                <button
                  id="refresh-members-btn"
                  className="btn-refresh"
                  onClick={loadMembers}
                  disabled={loadingMembers}
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                >
                  {loadingMembers ? 'Refreshing...' : 'Refresh Registry'}
                </button>
              </div>

              {loadingMembers && members.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', padding: '1.5rem 0' }}>
                  Loading registry database...
                </p>
              ) : members.length === 0 ? (
                <div style={{ padding: '2rem 0', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  No rescue members enrolled. Use the form above to enroll authorized emergency responders.
                </div>
              ) : (
                <div className="table-wrapper">
                  <table className="registry-table">
                    <thead>
                      <tr>
                        <th>Rescue ID</th>
                        <th>Device ID</th>
                        <th>Responder</th>
                        <th>Tactical Unit</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Cryptographic Keys</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {members.map((member) => {
                        const hasKeys = !!(member.signing_public_key && member.encryption_public_key);
                        const isRevoked = member.status === 'revoked';

                        return (
                          <tr key={member.rescue_id} className={isRevoked ? 'row-revoked' : ''}>
                            <td className="id-cell">{member.rescue_id}</td>
                            <td className="id-cell">{member.device_id}</td>
                            <td style={{ fontWeight: 600 }}>{member.name}</td>
                            <td>{member.team}</td>
                            <td>
                              <span className="role-tag">{member.role}</span>
                            </td>
                            <td>
                              <span className={`status-pill ${member.status}`}>
                                {member.status.toUpperCase()}
                              </span>
                            </td>
                            <td>
                              {hasKeys ? (
                                <span className="key-badge provisioned" title="Ed25519 & X25519 keys loaded in registry">
                                  PROVISIONED
                                </span>
                              ) : (
                                <span className="key-badge missing" title="Public keys not yet initialized">
                                  UNINITIALIZED
                                </span>
                              )}
                            </td>
                            <td>
                              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                                {!hasKeys && !isRevoked && (
                                  <button
                                    id={`provision-btn-${member.device_id}`}
                                    className="btn-action-provision"
                                    onClick={() => handleProvisionKeys(member)}
                                    disabled={provisioningId === member.device_id}
                                    title="Generate Ed25519 and X25519 keypairs for this device"
                                  >
                                    {provisioningId === member.device_id ? 'Generating...' : 'Generate Keys'}
                                  </button>
                                )}
                                {!isRevoked ? (
                                  <button
                                    id={`revoke-btn-${member.rescue_id}`}
                                    className="btn-action-revoke"
                                    onClick={() => handleRevoke(member)}
                                    disabled={revokingId === member.rescue_id}
                                  >
                                    {revokingId === member.rescue_id ? 'Revoking...' : 'Revoke'}
                                  </button>
                                ) : (
                                  <span style={{ fontSize: '0.8rem', color: 'var(--accent-rose)' }}>
                                    Deactivated
                                  </span>
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
          </section>
        </>
      )}

      {/* TAB 3: Standardized 10-Phase Roadmap */}
      {activeTab === 'roadmap' && (
        <section style={{ marginTop: '2rem' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            Standardized 10-Phase Architectural Roadmap
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '1.5rem' }}>
            Structured multi-phase execution ensuring strict security boundaries and complete auditability.
          </p>

          <div className="roadmap-grid">
            <div className="phase-card completed">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 01</span>
                <span className="phase-status-tag completed">COMPLETED</span>
              </div>
              <h4 className="phase-title">Foundation &amp; Architecture</h4>
              <p className="phase-desc">
                FastAPI backend, clean modular structure, safe atomic JSON storage, test suite, and baseline frontend.
              </p>
            </div>

            <div className="phase-card completed">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 02</span>
                <span className="phase-status-tag completed">COMPLETED</span>
              </div>
              <h4 className="phase-title">Rescue Registry &amp; Device IDs</h4>
              <p className="phase-desc">
                Trusted team registry, administrative Rescue/Device IDs, active/revoked lifecycle, and historical retention.
              </p>
            </div>

            <div className="phase-card completed">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 03</span>
                <span className="phase-status-tag completed">COMPLETED</span>
              </div>
              <h4 className="phase-title">Cryptographic Security Layer</h4>
              <p className="phase-desc">
                Ed25519 signing keypairs, X25519 key agreement, HKDF-SHA256, and ChaCha20-Poly1305 authenticated envelopes.
              </p>
            </div>

            <div className="phase-card completed">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 04</span>
                <span className="phase-status-tag completed">COMPLETED</span>
              </div>
              <h4 className="phase-title">Software Mesh Simulation</h4>
              <p className="phase-desc">
                BFS shortest-path routing, multi-hop packet relay, node outage resilience, TTL hop limits, and passive link sniffer tap.
              </p>
            </div>

            <div className="phase-card completed">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 05</span>
                <span className="phase-status-tag completed">COMPLETED</span>
              </div>
              <h4 className="phase-title">Secure Message Transmission</h4>
              <p className="phase-desc">
                Authenticated X25519 + ChaCha20-Poly1305 + HKDF-SHA256 payload encryption and Ed25519 canonical JSON signatures.
              </p>
            </div>

            <div className="phase-card active">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 06</span>
                <span className="phase-status-tag active">ACTIVE PHASE</span>
              </div>
              <h4 className="phase-title">Authorization Gate &amp; Controlled Decryption</h4>
              <p className="phase-desc">
                Recipient identity verification, registry status validation, Ed25519 signature checks, replay protection, and authorized payload decryption.
              </p>
            </div>

            <div className="phase-card">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 07</span>
                <span className="phase-status-tag planned">PLANNED</span>
              </div>
              <h4 className="phase-title">Packet-Sniffing Attack Simulation</h4>
              <p className="phase-desc">
                Side-by-side demonstration: unencrypted packet sniffing vs encrypted mesh payload confidentiality.
              </p>
            </div>

            <div className="phase-card">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 08</span>
                <span className="phase-status-tag planned">PLANNED</span>
              </div>
              <h4 className="phase-title">Dashboard &amp; Real-Time UI</h4>
              <p className="phase-desc">
                Interactive tactical operations dashboard with live mesh topology visualization and audit log.
              </p>
            </div>

            <div className="phase-card">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 09</span>
                <span className="phase-status-tag planned">PLANNED</span>
              </div>
              <h4 className="phase-title">Security &amp; Resilience Testing</h4>
              <p className="phase-desc">
                Adversarial tamper testing, replay attack validation, and revoked-member rejection tests.
              </p>
            </div>

            <div className="phase-card">
              <div className="phase-card-header">
                <span className="phase-num">PHASE 10</span>
                <span className="phase-status-tag planned">PLANNED</span>
              </div>
              <h4 className="phase-title">Final Integration &amp; Demo</h4>
              <p className="phase-desc">
                Comprehensive end-to-end disaster scenario demonstration ready for hackathon presentation.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="footer">
        <div>RESQ Security System &bull; Phase 6 End-to-End Encrypted Mesh Active</div>
        <div>Software-based Mesh Blackout Resilience Demo</div>
      </footer>
    </div>
  );
};

export default App;
