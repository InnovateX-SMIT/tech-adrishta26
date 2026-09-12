import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from './services/api';
import { HealthResponse, SystemInfoResponse, ConnectionState } from './types';

export const App: React.FC = () => {
  const [connectionState, setConnectionState] = useState<ConnectionState>('loading');
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastPingTime, setLastPingTime] = useState<string | null>(null);

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

  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

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
          <span className="phase-tag">Phase 1: Foundation Active</span>
          <button
            id="refresh-status-btn"
            className="btn-refresh"
            onClick={checkBackendHealth}
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
          <span>⚠️ Problem Statement Under Resolution</span>
        </div>
        <h2 className="hero-title">
          Unencrypted peer-to-peer mesh network vulnerable to packet sniffing during a blackout.
        </h2>
        <p className="hero-description">
          During civil blackout conditions when cellular towers and the internet fail, first responders
          rely on peer-to-peer mesh communications. Standard mesh topologies broadcast packets in plaintext,
          allowing adversaries to sniff sensitive medical reports and tactical rescue coordinates. RESQ
          establishes an authenticated, cryptographic mesh protocol where packets traverse multi-hop peers
          while remaining impervious to unauthorized packet sniffing.
        </p>
      </section>

      {/* Core Status Grid */}
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
                  <td className="label-col">API Endpoint</td>
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

        {/* Security Modules Status Card */}
        <div className="card" id="security-state-card">
          <div className="card-header">
            <h3 className="card-title">
              <span>Security State</span>
            </h3>
            <span className="status-pill loading">PHASE 1 INVARIANTS</span>
          </div>

          <table className="info-table">
            <tbody>
              <tr>
                <td className="label-col">Mesh Network Simulation</td>
                <td className="val-col">
                  <span className="val-badge inactive">
                    {systemInfo?.mesh_enabled ? 'ENABLED' : 'NOT YET ACTIVE (Phase 4)'}
                  </span>
                </td>
              </tr>
              <tr>
                <td className="label-col">End-to-End Encryption</td>
                <td className="val-col">
                  <span className="val-badge inactive">
                    {systemInfo?.encryption_enabled ? 'ENABLED' : 'NOT YET ACTIVE (Phase 3)'}
                  </span>
                </td>
              </tr>
              <tr>
                <td className="label-col">Attacker Packet Sniffer</td>
                <td className="val-col">
                  <span className="val-badge inactive">NOT YET ACTIVE (Phase 5)</span>
                </td>
              </tr>
              <tr>
                <td className="label-col">Local JSON Registry</td>
                <td className="val-col" style={{ color: 'var(--accent-cyan)' }}>
                  INITIALIZED (data/registry.json)
                </td>
              </tr>
              <tr>
                <td className="label-col">Cryptographic Key Storage</td>
                <td className="val-col" style={{ color: 'var(--accent-cyan)' }}>
                  SECURED (No private keys exposed)
                </td>
              </tr>
            </tbody>
          </table>

          <div className="notice-box warning">
            <strong>Strict Scope Note:</strong> Cryptographic keys, message encryption (X25519 / AES-GCM),
            and peer-to-peer mesh packet relay are scheduled for upcoming phases. No mocked or pseudo-encrypted
            data is transmitted in Phase 1.
          </div>
        </div>
      </div>

      {/* Architecture Roadmap */}
      <section style={{ marginTop: '2.5rem' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
          Architectural Implementation Roadmap
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '1rem' }}>
          Phased execution pipeline ensuring rigorous security boundaries and full auditability.
        </p>

        <div className="roadmap-grid">
          <div className="phase-card active">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 01</span>
              <span className="phase-status-tag active">COMPLETED FOUNDATION</span>
            </div>
            <h4 className="phase-title">Foundation & Architecture</h4>
            <p className="phase-desc">
              FastAPI backend, clean modular structure, atomic JSON store, test suite, and baseline frontend.
            </p>
          </div>

          <div className="phase-card">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 02</span>
              <span className="phase-status-tag planned">PLANNED</span>
            </div>
            <h4 className="phase-title">Registry & Identity</h4>
            <p className="phase-desc">
              Rescue team registry schema, device identity registration, and local keypair generation isolation.
            </p>
          </div>

          <div className="phase-card">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 03</span>
              <span className="phase-status-tag planned">PLANNED</span>
            </div>
            <h4 className="phase-title">Cryptography Pipeline</h4>
            <p className="phase-desc">
              X25519 ECDH key agreement, authenticated symmetric encryption (AES-GCM / ChaCha20), and Ed25519 signatures.
            </p>
          </div>

          <div className="phase-card">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 04</span>
              <span className="phase-status-tag planned">PLANNED</span>
            </div>
            <h4 className="phase-title">Mesh Network Simulation</h4>
            <p className="phase-desc">
              Multi-hop peer-to-peer relay simulation without plaintext exposure on intermediate nodes.
            </p>
          </div>

          <div className="phase-card">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 05</span>
              <span className="phase-status-tag planned">PLANNED</span>
            </div>
            <h4 className="phase-title">Attacker Sniffer & Verification</h4>
            <p className="phase-desc">
              Side-by-side comparison: unencrypted broadcast (vulnerable) vs RESQ encrypted mesh (confidential).
            </p>
          </div>

          <div className="phase-card">
            <div className="phase-card-header">
              <span className="phase-num">PHASE 06</span>
              <span className="phase-status-tag planned">PLANNED</span>
            </div>
            <h4 className="phase-title">Operational Rescue Dashboard</h4>
            <p className="phase-desc">
              Tactical interface for dispatching emergency signals, verifying responder status, and audit logs.
            </p>
          </div>
        </div>
      </section>

      {/* Future Data Contract Preview (Non-Active) */}
      <section style={{ marginTop: '2.5rem' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
          Conceptual Packet Contract (Planned for Phase 3)
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
          The structured cryptographic packet contract defined in <code>docs/architecture.md</code>:
        </p>

        <div className="contract-box">
          <pre>{`// FUTURE CONTRACT SPECIFICATION (Not active in Phase 1)
{
  "packet_id": "PKT-1001",
  "message_id": "MSG-1001",
  "sender_id": "RESQ-001",
  "recipient_id": "RESQ-002",
  "timestamp": 1773300000,
  "ephemeral_public_key": "<X25519-Ephemeral-Key>",
  "nonce": "<12-byte-IV>",
  "ciphertext": "<Authenticated-Ciphertext>",
  "signature": "<Ed25519-Sender-Signature>"
}`}</pre>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div>RESQ Security System &bull; Phase 1 Foundation</div>
        <div>Software-based Mesh Blackout Resilience Demo</div>
      </footer>
    </div>
  );
};

export default App;
