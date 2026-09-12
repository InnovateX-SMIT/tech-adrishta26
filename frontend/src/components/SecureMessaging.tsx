import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import {
  RescueMember,
  SendMessageResponse,
  InboxMessageSummary,
  DecryptMessageResponse,
} from '../types';

interface SecureMessagingProps {
  members: RescueMember[];
  onRefreshMembers: () => void;
}

export const SecureMessaging: React.FC<SecureMessagingProps> = ({
  members,
  onRefreshMembers,
}) => {
  // Active sender & recipient selection
  const [senderId, setSenderId] = useState<string>('');
  const [recipientId, setRecipientId] = useState<string>('');
  const [messageText, setMessageText] = useState<string>(
    'MAYDAY: Critical structural failure at Sector 7-G. 4 casualties. Immediate extraction required.'
  );
  const [priority, setPriority] = useState<string>('HIGH');

  // Transmission state
  const [sending, setSending] = useState<boolean>(false);
  const [sendSuccess, setSendSuccess] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [lastSentResponse, setLastSentResponse] = useState<SendMessageResponse | null>(null);

  // Inbox & Decryption state
  const [inspectDeviceId, setInspectDeviceId] = useState<string>('');
  const [inboxMessages, setInboxMessages] = useState<InboxMessageSummary[]>([]);
  const [loadingInbox, setLoadingInbox] = useState<boolean>(false);
  const [decryptingPacketId, setDecryptingPacketId] = useState<string | null>(null);
  const [decryptionResult, setDecryptionResult] = useState<DecryptMessageResponse | null>(null);
  const [decryptError, setDecryptError] = useState<string | null>(null);

  // Attack defense demonstration state
  const [tampering, setTampering] = useState<boolean>(false);

  // Auto-select initial active sender and recipient
  useEffect(() => {
    const activeMembers = members.filter((m) => m.status === 'active');
    if (activeMembers.length >= 2) {
      if (!senderId) setSenderId(activeMembers[0].rescue_id);
      if (!recipientId) setRecipientId(activeMembers[1].rescue_id);
      if (!inspectDeviceId) setInspectDeviceId(activeMembers[1].rescue_id);
    } else if (activeMembers.length === 1) {
      if (!senderId) setSenderId(activeMembers[0].rescue_id);
      if (!inspectDeviceId) setInspectDeviceId(activeMembers[0].rescue_id);
    }
  }, [members, senderId, recipientId, inspectDeviceId]);

  // Load recipient inbox
  const loadInbox = useCallback(async (targetId: string) => {
    if (!targetId) return;
    setLoadingInbox(true);
    setDecryptError(null);
    try {
      const messages = await apiService.fetchDeviceInbox(targetId);
      setInboxMessages(messages);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setDecryptError(err.message);
      } else {
        setDecryptError('Failed to load device inbox.');
      }
    } finally {
      setLoadingInbox(false);
    }
  }, []);

  useEffect(() => {
    if (inspectDeviceId) {
      loadInbox(inspectDeviceId);
    }
  }, [inspectDeviceId, loadInbox]);

  // Handle Send Secure Message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    setSendError(null);
    setSendSuccess(null);

    if (!senderId) {
      setSendError('Please select an active sender.');
      return;
    }
    if (!recipientId) {
      setSendError('Please select an active recipient.');
      return;
    }
    if (senderId === recipientId) {
      setSendError('Sender and recipient must be distinct rescue units.');
      return;
    }
    if (!messageText.trim()) {
      setSendError('Message content cannot be empty.');
      return;
    }

    setSending(true);
    try {
      const resp = await apiService.sendSecureMessage({
        sender_id: senderId,
        recipient_id: recipientId,
        message: messageText.trim(),
        priority,
      });

      setLastSentResponse(resp);
      setSendSuccess(
        `Dispatched ${resp.packet_id} across ${resp.hop_log.length} mesh hop(s) successfully.`
      );

      // If currently inspecting recipient device, refresh its inbox automatically
      if (
        inspectDeviceId === recipientId ||
        members.find((m) => m.rescue_id === recipientId)?.device_id === inspectDeviceId
      ) {
        await loadInbox(inspectDeviceId);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setSendError(err.message);
      } else {
        setSendError('Failed to send secure message.');
      }
    } finally {
      setSending(false);
    }
  };

  // Handle Decrypt Inbox Message
  const handleDecryptInboxMessage = async (packetId: string) => {
    setDecryptingPacketId(packetId);
    setDecryptionResult(null);
    setDecryptError(null);

    try {
      const resp = await apiService.decryptMessage({
        recipient_id: inspectDeviceId,
        packet_id: packetId,
      });
      setDecryptionResult(resp);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setDecryptError(err.message);
      } else {
        setDecryptError('Decryption gate execution failed.');
      }
    } finally {
      setDecryptingPacketId(null);
    }
  };

  // Defense Test: Tamper with ciphertext
  const handleTestTamperDefense = async () => {
    if (!lastSentResponse) return;
    setTampering(true);
    setDecryptionResult(null);
    setDecryptError(null);

    try {
      // Intentionally corrupt ciphertext string
      const tamperedPayload = {
        ...lastSentResponse.payload,
        ciphertext: 'TAMPERED' + lastSentResponse.payload.ciphertext.slice(8),
      };

      const resp = await apiService.decryptMessage({
        recipient_id: inspectDeviceId || lastSentResponse.recipient_id,
        payload: tamperedPayload,
      });
      setDecryptionResult(resp);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setDecryptError(err.message);
      }
    } finally {
      setTampering(false);
    }
  };

  // Defense Test: Replay attack
  const handleTestReplayDefense = async () => {
    if (!lastSentResponse) return;
    setTampering(true);
    setDecryptionResult(null);
    setDecryptError(null);

    try {
      // Directly submit the exact same payload a second time
      const resp = await apiService.decryptMessage({
        recipient_id: inspectDeviceId || lastSentResponse.recipient_id,
        payload: lastSentResponse.payload,
      });
      setDecryptionResult(resp);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setDecryptError(err.message);
      }
    } finally {
      setTampering(false);
    }
  };

  const senderMember = members.find(
    (m) => m.rescue_id === senderId || m.device_id === senderId
  );
  const recipientMember = members.find(
    (m) => m.rescue_id === recipientId || m.device_id === recipientId
  );
  const inspectingMember = members.find(
    (m) => m.rescue_id === inspectDeviceId || m.device_id === inspectDeviceId
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Overview Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.12), rgba(16, 185, 129, 0.08))',
          border: '1px solid rgba(6, 182, 212, 0.3)',
          borderRadius: 'var(--radius-md)',
          padding: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.35rem' }}>
            <span
              style={{
                background: 'var(--accent-emerald)',
                color: '#000',
                fontSize: '0.72rem',
                fontWeight: 800,
                padding: '0.2rem 0.6rem',
                borderRadius: '999px',
                letterSpacing: '0.04em',
              }}
            >
              PHASE 6 ACTIVE
            </span>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              End-to-End Secure Transmission &amp; Authorization Gate
            </h2>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '780px' }}>
            Transmits authenticated emergency distress dispatches over multi-hop mesh topologies using{' '}
            <strong style={{ color: 'var(--accent-cyan)' }}>X25519 + ChaCha20-Poly1305 + HKDF-SHA256</strong>, signed with{' '}
            <strong style={{ color: 'var(--accent-amber)' }}>Ed25519</strong>. The Phase 6 authorization gate strictly enforces
            registry lookup, active status, digital signature, recipient authorization, and replay protection before releasing plaintext.
          </p>
        </div>

        <button
          onClick={() => {
            onRefreshMembers();
            if (inspectDeviceId) loadInbox(inspectDeviceId);
          }}
          className="btn-secondary"
          style={{ padding: '0.55rem 1rem', fontSize: '0.82rem' }}
        >
          ↻ Refresh System State
        </button>
      </div>

      {/* Main Two-Column Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))',
          gap: '2rem',
        }}
      >
        {/* ================================================================= */}
        {/* COLUMN 1: SECURE MESSAGE COMPOSER & WIRE PACKET INSPECTOR         */}
        {/* ================================================================= */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Composer Card */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '1.5rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
              <span style={{ fontSize: '1.2rem' }}>🔒</span>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Compose Authenticated Distress Dispatch</h3>
            </div>

            <form onSubmit={handleSendMessage} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
              {/* Sender & Recipient Pickers */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.35rem', fontWeight: 600 }}>
                    Sender Identity (Signer)
                  </label>
                  <select
                    value={senderId}
                    onChange={(e) => setSenderId(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.6rem 0.75rem',
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.85rem',
                    }}
                  >
                    <option value="">Select Sender...</option>
                    {members.map((m) => (
                      <option key={m.rescue_id} value={m.rescue_id} disabled={m.status !== 'active'}>
                        {m.name} ({m.rescue_id}) {m.status === 'revoked' ? '[REVOKED]' : ''}
                      </option>
                    ))}
                  </select>
                  {senderMember && (
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.2rem', display: 'block' }}>
                      Device: {senderMember.device_id} &bull; Signing Key: {senderMember.signing_public_key ? '✓ Available' : '✗ Missing'}
                    </span>
                  )}
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.35rem', fontWeight: 600 }}>
                    Recipient Identity (Decryptor)
                  </label>
                  <select
                    value={recipientId}
                    onChange={(e) => setRecipientId(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.6rem 0.75rem',
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.85rem',
                    }}
                  >
                    <option value="">Select Recipient...</option>
                    {members.map((m) => (
                      <option key={m.rescue_id} value={m.rescue_id} disabled={m.status !== 'active'}>
                        {m.name} ({m.rescue_id}) {m.status === 'revoked' ? '[REVOKED]' : ''}
                      </option>
                    ))}
                  </select>
                  {recipientMember && (
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.2rem', display: 'block' }}>
                      Device: {recipientMember.device_id} &bull; Encryption Key: {recipientMember.encryption_public_key ? '✓ Available' : '✗ Missing'}
                    </span>
                  )}
                </div>
              </div>

              {/* Priority & Plaintext Input */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                  <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    Emergency Plaintext Content
                  </label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Priority:</span>
                    <select
                      value={priority}
                      onChange={(e) => setPriority(e.target.value)}
                      style={{
                        padding: '0.2rem 0.5rem',
                        background: 'rgba(0,0,0,0.3)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '4px',
                        color: 'var(--accent-amber)',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                      }}
                    >
                      <option value="NORMAL">NORMAL</option>
                      <option value="HIGH">HIGH</option>
                      <option value="CRITICAL">CRITICAL</option>
                    </select>
                  </div>
                </div>
                <textarea
                  rows={3}
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                  placeholder="Enter distress call, casualty report, or rescue coordinates..."
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: 'rgba(0,0,0,0.3)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    fontSize: '0.88rem',
                    resize: 'vertical',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              {/* Status alerts */}
              {sendError && (
                <div
                  style={{
                    background: 'rgba(244, 63, 94, 0.15)',
                    border: '1px solid var(--accent-rose)',
                    color: 'var(--accent-rose)',
                    padding: '0.65rem 0.85rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.82rem',
                  }}
                >
                  <strong>Transmission Error:</strong> {sendError}
                </div>
              )}

              {sendSuccess && (
                <div
                  style={{
                    background: 'rgba(16, 185, 129, 0.15)',
                    border: '1px solid var(--accent-emerald)',
                    color: 'var(--accent-emerald)',
                    padding: '0.65rem 0.85rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.82rem',
                  }}
                >
                  <strong>Success:</strong> {sendSuccess}
                </div>
              )}

              <button
                type="submit"
                disabled={sending}
                style={{
                  background: 'linear-gradient(135deg, #06b6d4, #0284c7)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.8rem 1.25rem',
                  fontWeight: 700,
                  fontSize: '0.92rem',
                  cursor: sending ? 'not-allowed' : 'pointer',
                  boxShadow: '0 0 15px var(--accent-cyan-glow)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                }}
              >
                {sending ? 'Encrypting & Transmitting...' : '🔒 Encrypt, Sign & Dispatch to Mesh'}
              </button>
            </form>
          </div>

          {/* Wire Packet Inspector */}
          {lastSentResponse && (
            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                borderRadius: 'var(--radius-md)',
                padding: '1.5rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '1.1rem' }}>📦</span>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700 }}>Wire Packet Payload Inspector</h4>
                </div>
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    background: 'rgba(16, 185, 129, 0.2)',
                    color: 'var(--accent-emerald)',
                    padding: '0.2rem 0.55rem',
                    borderRadius: '999px',
                    border: '1px solid var(--accent-emerald)',
                  }}
                >
                  ZERO PLAINTEXT ON WIRE
                </span>
              </div>

              {/* Hop Trail */}
              <div
                style={{
                  background: 'rgba(0,0,0,0.3)',
                  padding: '0.65rem 0.85rem',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '1rem',
                  fontSize: '0.82rem',
                }}
              >
                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.3rem' }}>
                  Forwarding Path ({lastSentResponse.hop_log.length} Hops):
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{lastSentResponse.sender_id}</span>
                  {lastSentResponse.hop_log.map((h, idx) => (
                    <React.Fragment key={idx}>
                      <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{h.to_node}</span>
                    </React.Fragment>
                  ))}
                  <span style={{ color: 'var(--text-muted)' }}>&rarr;</span>
                  <span style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}>{lastSentResponse.recipient_id}</span>
                </div>
              </div>

              {/* Payload Field Details */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.3rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Packet ID:</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{lastSentResponse.payload.packet_id}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.3rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Cipher Suite:</span>
                  <span style={{ color: 'var(--accent-cyan)' }}>
                    {lastSentResponse.payload.cipher} / {lastSentResponse.payload.kdf} / {lastSentResponse.payload.key_agreement}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.3rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Ephemeral Pub (X25519):</span>
                  <span style={{ color: 'var(--text-secondary)' }} title={lastSentResponse.payload.ephemeral_public_key}>
                    {lastSentResponse.payload.ephemeral_public_key.slice(0, 24)}... (32B B64)
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.3rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Salt / Nonce:</span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    Salt: {lastSentResponse.payload.salt} &bull; Nonce: {lastSentResponse.payload.nonce}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.3rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Ciphertext + Tag:</span>
                  <span style={{ color: 'var(--accent-amber)' }} title={lastSentResponse.payload.ciphertext}>
                    {lastSentResponse.payload.ciphertext.slice(0, 28)}... ({lastSentResponse.payload.ciphertext.length} chars)
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.3rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Ed25519 Signature:</span>
                  <span style={{ color: 'var(--accent-emerald)' }} title={lastSentResponse.payload.signature}>
                    {lastSentResponse.payload.signature.slice(0, 28)}... (64B B64)
                  </span>
                </div>
              </div>

              {/* Attack Demonstration Controls */}
              <div
                style={{
                  marginTop: '1.25rem',
                  paddingTop: '1rem',
                  borderTop: '1px dashed var(--border-subtle)',
                  display: 'flex',
                  gap: '0.75rem',
                  flexWrap: 'wrap',
                }}
              >
                <button
                  onClick={handleTestTamperDefense}
                  disabled={tampering}
                  style={{
                    flex: 1,
                    padding: '0.5rem 0.75rem',
                    background: 'rgba(244, 63, 94, 0.15)',
                    border: '1px solid var(--accent-rose)',
                    color: 'var(--accent-rose)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    cursor: tampering ? 'not-allowed' : 'pointer',
                  }}
                >
                  ⚡ Test Tamper Defense
                </button>
                <button
                  onClick={handleTestReplayDefense}
                  disabled={tampering}
                  style={{
                    flex: 1,
                    padding: '0.5rem 0.75rem',
                    background: 'rgba(245, 158, 11, 0.15)',
                    border: '1px solid var(--accent-amber)',
                    color: 'var(--accent-amber)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    cursor: tampering ? 'not-allowed' : 'pointer',
                  }}
                >
                  ⚡ Test Replay Defense
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* COLUMN 2: RECIPIENT INBOX & PHASE 6 CONTROLLED DECRYPTION GATE   */}
        {/* ================================================================= */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Recipient Device Inbox Card */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '1.5rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '1.2rem' }}>📬</span>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Recipient Device Inbox</h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <select
                  value={inspectDeviceId}
                  onChange={(e) => setInspectDeviceId(e.target.value)}
                  style={{
                    padding: '0.45rem 0.75rem',
                    background: 'rgba(0,0,0,0.3)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    fontSize: '0.82rem',
                  }}
                >
                  <option value="">Select Inspect Device...</option>
                  {members.map((m) => (
                    <option key={m.rescue_id} value={m.rescue_id}>
                      {m.name} ({m.rescue_id} / {m.device_id})
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => loadInbox(inspectDeviceId)}
                  disabled={loadingInbox || !inspectDeviceId}
                  className="btn-secondary"
                  style={{ padding: '0.45rem 0.75rem', fontSize: '0.8rem' }}
                >
                  {loadingInbox ? '...' : '↻'}
                </button>
              </div>
            </div>

            {inspectingMember && (
              <div
                style={{
                  background: 'rgba(0,0,0,0.25)',
                  padding: '0.6rem 0.8rem',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '1rem',
                  fontSize: '0.78rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span>
                  Inspecting: <strong>{inspectingMember.name}</strong> ({inspectingMember.rescue_id})
                </span>
                <span style={{ color: inspectingMember.status === 'active' ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                  ● {inspectingMember.status.toUpperCase()}
                </span>
              </div>
            )}

            {/* Inbox Message List */}
            {loadingInbox ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                Loading device inbox...
              </div>
            ) : inboxMessages.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📭</div>
                <div style={{ fontSize: '0.9rem' }}>No encrypted packets currently in this device inbox.</div>
                <div style={{ fontSize: '0.78rem', marginTop: '0.25rem' }}>
                  Dispatch a message from the left panel to route packets to this node.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '280px', overflowY: 'auto' }}>
                {inboxMessages.map((item) => {
                  const isProcessing = decryptingPacketId === item.packet_id;
                  return (
                    <div
                      key={item.packet_id}
                      style={{
                        background: 'rgba(0,0,0,0.3)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '0.85rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '0.75rem',
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--accent-cyan)' }}>
                            {item.packet_id}
                          </span>
                          <span
                            style={{
                              fontSize: '0.68rem',
                              padding: '0.15rem 0.4rem',
                              background: 'rgba(245, 158, 11, 0.2)',
                              color: 'var(--accent-amber)',
                              borderRadius: '4px',
                            }}
                          >
                            ENCRYPTED
                          </span>
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                          From: <strong>{item.sender_rescue_id}</strong> &bull; {new Date(item.timestamp * 1000).toLocaleTimeString()}
                        </div>
                      </div>

                      <button
                        onClick={() => handleDecryptInboxMessage(item.packet_id)}
                        disabled={isProcessing}
                        style={{
                          background: 'linear-gradient(135deg, #10b981, #059669)',
                          color: '#fff',
                          border: 'none',
                          borderRadius: 'var(--radius-sm)',
                          padding: '0.45rem 0.9rem',
                          fontSize: '0.8rem',
                          fontWeight: 700,
                          cursor: isProcessing ? 'not-allowed' : 'pointer',
                          boxShadow: '0 0 10px var(--accent-emerald-glow)',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {isProcessing ? 'Verifying...' : 'Authorize & Decrypt'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Phase 6 Controlled Decryption Gate Visualizer */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: decryptionResult
                ? decryptionResult.status === 'SUCCESS'
                  ? '1px solid var(--accent-emerald)'
                  : '1px solid var(--accent-rose)'
                : '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '1.5rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '1.1rem' }}>🛡️</span>
                <h4 style={{ fontSize: '1rem', fontWeight: 700 }}>Phase 6 Authorization Gate Decisions</h4>
              </div>
              {decryptionResult && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 800,
                    padding: '0.2rem 0.6rem',
                    borderRadius: '999px',
                    background:
                      decryptionResult.status === 'SUCCESS'
                        ? 'rgba(16, 185, 129, 0.2)'
                        : 'rgba(244, 63, 94, 0.2)',
                    color:
                      decryptionResult.status === 'SUCCESS'
                        ? 'var(--accent-emerald)'
                        : 'var(--accent-rose)',
                    border:
                      decryptionResult.status === 'SUCCESS'
                        ? '1px solid var(--accent-emerald)'
                        : '1px solid var(--accent-rose)',
                  }}
                >
                  GATE DECISION: {decryptionResult.status}
                </span>
              )}
            </div>

            {/* 6 Strict Gate Checkpoints */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', marginBottom: '1.25rem' }}>
              {[
                {
                  step: 1,
                  name: 'Sender Registry Lookup',
                  desc: 'Verifies sender identity exists in the trusted rescue directory',
                  passed: decryptionResult?.status === 'SUCCESS' || (decryptionResult?.status === 'REJECTED' && decryptionResult.reason !== 'UNKNOWN_SENDER'),
                  failed: decryptionResult?.status === 'REJECTED' && decryptionResult.reason === 'UNKNOWN_SENDER',
                },
                {
                  step: 2,
                  name: 'Member Status Validation',
                  desc: 'Ensures sender member is active and not revoked',
                  passed: decryptionResult?.status === 'SUCCESS' || (decryptionResult?.status === 'REJECTED' && !decryptionResult.reason?.startsWith('SENDER_')),
                  failed: decryptionResult?.status === 'REJECTED' && decryptionResult.reason?.startsWith('SENDER_'),
                },
                {
                  step: 3,
                  name: 'Ed25519 Digital Signature Verification',
                  desc: 'Verifies authentic signature over RFC 8785 canonical JSON metadata + ciphertext',
                  passed: decryptionResult?.status === 'SUCCESS' || (decryptionResult?.status === 'REJECTED' && decryptionResult.reason !== 'INVALID_SIGNATURE'),
                  failed: decryptionResult?.status === 'REJECTED' && decryptionResult.reason === 'INVALID_SIGNATURE',
                },
                {
                  step: 4,
                  name: 'Recipient Authorization Enforcement',
                  desc: 'Ensures current device is the authorized cryptographic destination',
                  passed: decryptionResult?.status === 'SUCCESS' || (decryptionResult?.status === 'REJECTED' && decryptionResult.reason !== 'UNAUTHORIZED_RECIPIENT'),
                  failed: decryptionResult?.status === 'REJECTED' && decryptionResult.reason === 'UNAUTHORIZED_RECIPIENT',
                },
                {
                  step: 5,
                  name: 'Protocol Replay & Drift Check',
                  desc: 'Detects duplicate packet_ids and rejects expired timestamp drift',
                  passed: decryptionResult?.status === 'SUCCESS' || (decryptionResult?.status === 'REJECTED' && decryptionResult.reason !== 'REPLAY_ATTACK_DETECTED' && decryptionResult.reason !== 'TIMESTAMP_EXPIRED'),
                  failed: decryptionResult?.status === 'REJECTED' && (decryptionResult.reason === 'REPLAY_ATTACK_DETECTED' || decryptionResult.reason === 'TIMESTAMP_EXPIRED'),
                },
                {
                  step: 6,
                  name: 'ChaCha20-Poly1305 AEAD Decryption',
                  desc: 'Derives symmetric key via HKDF-SHA256 and validates 16-byte Poly1305 MAC tag with AAD',
                  passed: decryptionResult?.status === 'SUCCESS',
                  failed: decryptionResult?.status === 'REJECTED' && decryptionResult.reason === 'DECRYPTION_FAILED',
                },
              ].map((c) => {
                const isActive = decryptionResult !== null;
                return (
                  <div
                    key={c.step}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.45rem 0.75rem',
                      background: 'rgba(0,0,0,0.2)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.78rem',
                    }}
                  >
                    <div>
                      <span style={{ fontWeight: 700, color: 'var(--text-primary)', marginRight: '0.5rem' }}>
                        Check {c.step}: {c.name}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>{c.desc}</span>
                    </div>
                    <div>
                      {!isActive ? (
                        <span style={{ color: 'var(--text-muted)' }}>Standby</span>
                      ) : c.failed ? (
                        <span style={{ color: 'var(--accent-rose)', fontWeight: 800 }}>FAILED ✗</span>
                      ) : (
                        <span style={{ color: 'var(--accent-emerald)', fontWeight: 800 }}>PASSED ✓</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Controlled Plaintext Reveal or Suppression */}
            {decryptionResult?.status === 'SUCCESS' && (
              <div
                style={{
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid var(--accent-emerald)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '1rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)', fontWeight: 700 }}>
                    AUTHENTICATED SENDER: {decryptionResult.sender_name} ({decryptionResult.sender_id})
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Packet: {decryptionResult.packet_id}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: '0.95rem',
                    color: 'var(--text-primary)',
                    fontWeight: 600,
                    lineHeight: 1.5,
                    marginBottom: '0.5rem',
                  }}
                >
                  "{decryptionResult.message}"
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Plaintext released safely. Zero sensitive data was leaked during multi-hop transmission.
                </div>
              </div>
            )}

            {decryptionResult?.status === 'REJECTED' && (
              <div
                style={{
                  background: 'rgba(244, 63, 94, 0.12)',
                  border: '1px solid var(--accent-rose)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '1rem',
                }}
              >
                <div style={{ fontSize: '0.8rem', color: 'var(--accent-rose)', fontWeight: 700, marginBottom: '0.35rem' }}>
                  ACCESS DENIED: {decryptionResult.reason}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  The Phase 6 decryption gate suppressed plaintext release because the message failed security verification.
                  Neither plaintext nor cryptographic keys were leaked.
                </div>
              </div>
            )}

            {decryptError && (
              <div
                style={{
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid var(--accent-rose)',
                  color: 'var(--accent-rose)',
                  padding: '0.65rem 0.85rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.82rem',
                  marginTop: '0.75rem',
                }}
              >
                <strong>Error:</strong> {decryptError}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
