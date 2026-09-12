import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from './services/api';
import {
  HealthResponse,
  SystemInfoResponse,
  ConnectionState,
  RescueMember,
} from './types';

export const App: React.FC = () => {
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
          <span className="phase-tag">Phase 3: Cryptography Active</span>
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
          <span>⚠️ Blackout Threat Model</span>
        </div>
        <h2 className="hero-title">
          Unencrypted peer-to-peer mesh network vulnerable to packet sniffing during a blackout.
        </h2>
        <p className="hero-description">
          During infrastructure blackout conditions, rescue teams deploy ad-hoc peer-to-peer mesh relays.
          In Phase 3, RESQ anchors the network with cryptographic primitives: Ed25519 digital signatures,
          X25519 Diffie-Hellman key agreement, HKDF-SHA256 key derivation with per-message random salt,
          and ChaCha20-Poly1305 authenticated encryption with fresh 12-byte nonces.
        </p>
      </section>

      {/* Backend Infrastructure Status Grid */}
      <div className="grid-2">
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
            <span className="status-pill active">PHASE 3 ACTIVE</span>
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
                <td className="val-col">
                  <span className="val-badge inactive">NOT YET ACTIVE (Phase 4)</span>
                </td>
              </tr>
              <tr>
                <td className="label-col">Attacker Packet Sniffer</td>
                <td className="val-col">
                  <span className="val-badge inactive">NOT YET ACTIVE (Phase 7)</span>
                </td>
              </tr>
            </tbody>
          </table>

          <div className="notice-box warning">
            <strong>Security Boundary Notice:</strong> Phase 3 implements cryptographic key generation, digital signatures,
            and ChaCha20-Poly1305 authenticated envelopes. Local private keys are stored on the host filesystem under
            <code>keys/&lt;device_id&gt;/</code> (development prototype) and are never exposed over APIs or in the browser.
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
                type="submit"
                className="btn-primary"
                disabled={submittingReg || !regName.trim() || !regTeam.trim() || !regRole.trim()}
              >
                {submittingReg ? 'Registering...' : '+ Register Responder'}
              </button>
            </div>
          </form>
        </div>

        {/* Registered Members Table */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <span>Registry Members &amp; Devices</span>
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {members.length} {members.length === 1 ? 'Record' : 'Records'}
            </span>
          </div>

          {loadingMembers ? (
            <p style={{ color: 'var(--text-secondary)', padding: '2rem 0', textAlign: 'center' }}>
              Loading registry records...
            </p>
          ) : members.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-secondary)' }}>
              <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>No responders registered in data/registry.json</p>
              <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                Use the registration form above to enroll rescue personnel and provision device identifiers.
              </p>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rescue ID</th>
                    <th>Name</th>
                    <th>Team</th>
                    <th>Role</th>
                    <th>Device ID</th>
                    <th>Status</th>
                    <th>Cryptographic Keys</th>
                    <th>Registered (UTC)</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((m) => {
                    const hasKeys = m.signing_public_key && m.encryption_public_key;
                    return (
                      <tr key={m.rescue_id}>
                        <td><span className="code-pill">{m.rescue_id}</span></td>
                        <td style={{ fontWeight: 600 }}>{m.name}</td>
                        <td>{m.team}</td>
                        <td style={{ color: 'var(--text-secondary)' }}>{m.role}</td>
                        <td><span className="code-pill">{m.device_id}</span></td>
                        <td>
                          <span className={`status-pill ${m.status}`}>
                            <span className="dot" />
                            {m.status.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          {hasKeys ? (
                            <span className="status-pill active" title="Ed25519 & X25519 Initialized">
                              <span className="dot" />
                              INITIALIZED (Ed25519 / X25519)
                            </span>
                          ) : m.status === 'active' ? (
                            <button
                              className="btn-provision"
                              onClick={() => handleProvisionKeys(m)}
                              disabled={provisioningId === m.device_id}
                            >
                              {provisioningId === m.device_id ? 'Provisioning...' : 'Provision Keys'}
                            </button>
                          ) : (
                            <span className="readiness-pill">Not initialized</span>
                          )}
                        </td>
                        <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {m.created_at ? new Date(m.created_at).toLocaleString() : 'N/A'}
                        </td>
                        <td>
                          {m.status === 'active' ? (
                            <button
                              className="btn-revoke"
                              onClick={() => handleRevoke(m)}
                              disabled={revokingId === m.rescue_id || provisioningId === m.device_id}
                            >
                              {revokingId === m.rescue_id ? 'Revoking...' : 'Revoke'}
                            </button>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: 'var(--accent-rose)', fontStyle: 'italic' }}>
                              Revoked
                            </span>
                          )}
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

      {/* Standardized 10-Phase Roadmap */}
      <section style={{ marginTop: '3rem' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
          Standardized 10-Phase Architectural Roadmap
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '1rem' }}>
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

          <div className="phase-card active">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 03</span>
              <span className="phase-status-tag active">ACTIVE PHASE</span>
            </div>
            <h4 className="phase-title">Cryptographic Security Layer</h4>
            <p className="phase-desc">
              Ed25519 signing keypairs, X25519 key agreement, HKDF-SHA256, and ChaCha20-Poly1305 authenticated envelopes.
            </p>
          </div>

          <div className="phase-card">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 04</span>
              <span className="phase-status-tag planned">PLANNED</span>
            </div>
            <h4 className="phase-title">Software Mesh Simulation</h4>
            <p className="phase-desc">
              In-process peer-to-peer relay simulation without plaintext exposure on intermediate hops.
            </p>
          </div>

          <div className="phase-card">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 05</span>
              <span className="phase-status-tag planned">PLANNED</span>
            </div>
            <h4 className="phase-title">Secure Message Transmission</h4>
            <p className="phase-desc">
              Authenticated payload encryption and Ed25519 packet signing over mesh topologies.
            </p>
          </div>

          <div className="phase-card">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 06</span>
              <span className="phase-status-tag planned">PLANNED</span>
            </div>
            <h4 className="phase-title">Authorization &amp; Decryption</h4>
            <p className="phase-desc">
              Recipient identity verification, registry status validation, and authorized payload decryption.
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

      {/* Footer */}
      <footer className="footer">
        <div>RESQ Security System &bull; Phase 3 Cryptographic Layer Active</div>
        <div>Software-based Mesh Blackout Resilience Demo</div>
      </footer>
    </div>
  );
};

export default App;
