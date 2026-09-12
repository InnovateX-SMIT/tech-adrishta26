import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import {
  RescueMember,
  SendMessageResponse,
  InboxMessageSummary,
  DecryptMessageResponse,
} from '../types';
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  Unlock,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileText,
} from 'lucide-react';
import { SectionHeader } from './layout/SectionHeader';

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
        message: messageText,
        priority: priority,
      });

      setLastSentResponse(resp);
      setSendSuccess(
        `Dispatched ${resp.packet_id.slice(0, 8)} across ${resp.hop_log.length} mesh hop(s) successfully.`
      );

      // Refresh inbox if currently inspecting recipient device
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

  return (
    <div className="space-y-8 animate-fade-in">
      {/* 1. Header Banner */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 border-b border-slate-800/70 pb-5">
        <div className="flex items-center gap-3.5">
          <div className="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
            <Lock className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-black text-slate-100 uppercase tracking-tight">
                Secure Transmission Console
              </h1>
              <span className="px-2.5 py-0.5 text-[9px] font-black uppercase tracking-widest bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                Phase 5 & 6 Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              End-to-end encrypted mesh messaging with{' '}
              <strong className="text-cyan-400 font-mono">ECDH (X25519) + ChaCha20-Poly1305 + HKDF-SHA256</strong>, signed with{' '}
              <strong className="text-amber-400 font-mono">Ed25519</strong>. The authorization gate enforces strict signature validation, registry lookup, and replay defense before releasing plaintext.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            onRefreshMembers();
            if (inspectDeviceId) loadInbox(inspectDeviceId);
          }}
          className="px-4 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-slate-100 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2 shrink-0 self-start xl:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
          Refresh State
        </button>
      </div>

      {/* 2. Main Two-Column Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
        {/* ================================================================= */}
        {/* COLUMN 1: COMPOSER & WIRE PACKET INSPECTOR (6 cols)              */}
        {/* ================================================================= */}
        <div className="xl:col-span-6 space-y-6">
          {/* Composer Card */}
          <div className="glass-card rounded-2xl border border-slate-800/60 p-6 relative overflow-hidden">
            <SectionHeader
              title="Compose Authenticated Distress Dispatch"
              accentColor="bg-indigo-500"
            />

            <form onSubmit={handleSendMessage} className="space-y-4">
              {/* Sender & Recipient Dropdowns */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                    Sender Identity (Signer)
                  </label>
                  <select
                    value={senderId}
                    onChange={(e) => setSenderId(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    <option value="">Select Sender...</option>
                    {members.map((m) => (
                      <option key={m.rescue_id} value={m.rescue_id} disabled={m.status !== 'active'}>
                        {m.name} ({m.rescue_id}) {m.status === 'revoked' ? '[REVOKED]' : ''}
                      </option>
                    ))}
                  </select>
                  {senderMember && (
                    <span className="text-[10px] text-slate-500 mt-1 block font-mono">
                      Device: {senderMember.device_id} • Key:{' '}
                      <span className={senderMember.signing_public_key ? 'text-emerald-400' : 'text-red-400'}>
                        {senderMember.signing_public_key ? '✓ Available' : '✗ Missing'}
                      </span>
                    </span>
                  )}
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                    Recipient Identity (Decryptor)
                  </label>
                  <select
                    value={recipientId}
                    onChange={(e) => setRecipientId(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    <option value="">Select Recipient...</option>
                    {members.map((m) => (
                      <option key={m.rescue_id} value={m.rescue_id} disabled={m.status !== 'active'}>
                        {m.name} ({m.rescue_id}) {m.status === 'revoked' ? '[REVOKED]' : ''}
                      </option>
                    ))}
                  </select>
                  {recipientMember && (
                    <span className="text-[10px] text-slate-500 mt-1 block font-mono">
                      Device: {recipientMember.device_id} • Key:{' '}
                      <span className={recipientMember.encryption_public_key ? 'text-emerald-400' : 'text-red-400'}>
                        {recipientMember.encryption_public_key ? '✓ Available' : '✗ Missing'}
                      </span>
                    </span>
                  )}
                </div>
              </div>

              {/* Priority & Plaintext Input */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Emergency Plaintext Message
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase font-bold text-slate-500">Priority:</span>
                    <select
                      value={priority}
                      onChange={(e) => setPriority(e.target.value)}
                      className="bg-slate-900 border border-slate-800 rounded-lg px-2 py-0.5 text-[11px] font-bold text-amber-400 outline-none cursor-pointer"
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
                  className="w-full bg-slate-900/60 border border-slate-700/60 text-slate-200 text-xs rounded-xl p-3 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-colors placeholder:text-slate-600 outline-none font-medium leading-relaxed resize-none"
                />
              </div>

              {/* Status alerts */}
              {sendError && (
                <div className="flex items-center gap-2.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl p-3 text-xs animate-shake">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{sendError}</span>
                </div>
              )}

              {sendSuccess && (
                <div className="flex items-center gap-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl p-3 text-xs animate-fade-in">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{sendSuccess}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={sending}
                className="w-full py-3 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:from-slate-800 disabled:to-slate-800 border border-indigo-500/20 text-white font-black text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-indigo-600/20 transition-all cursor-pointer flex items-center justify-center gap-2 disabled:cursor-not-allowed"
              >
                {sending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Encrypting, Signing & Forwarding...
                  </>
                ) : (
                  <>
                    <Lock className="w-4 h-4" />
                    Encrypt, Sign & Dispatch to Mesh
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Wire Packet Payload Inspector */}
          {lastSentResponse && (
            <div className="glass-card rounded-2xl border border-cyan-500/30 p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800/60">
                <SectionHeader title="Wire Packet Inspector" accentColor="bg-cyan-500" className="mb-0" />
                <span className="px-2.5 py-0.5 text-[9px] font-mono font-bold uppercase tracking-widest bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full">
                  Zero Plaintext on Wire
                </span>
              </div>

              {/* Hop Trail */}
              <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-900 text-xs">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
                  Mesh Forwarding Path ({lastSentResponse.hop_log.length} Hops):
                </span>
                <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
                  <span className="font-bold text-cyan-400">{lastSentResponse.sender_id}</span>
                  {lastSentResponse.hop_log.map((h, idx) => (
                    <React.Fragment key={idx}>
                      <span className="text-slate-600">➔</span>
                      <span className="text-slate-300 font-semibold">{h.to_node}</span>
                    </React.Fragment>
                  ))}
                  <span className="text-slate-600">➔</span>
                  <span className="font-bold text-emerald-400">{lastSentResponse.recipient_id}</span>
                </div>
              </div>

              {/* Payload Field Details */}
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between items-center py-1 border-b border-slate-900">
                  <span className="text-slate-500 text-[10px] uppercase font-bold">Packet ID:</span>
                  <span className="text-slate-200 font-bold">{lastSentResponse.payload.packet_id}</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-slate-900">
                  <span className="text-slate-500 text-[10px] uppercase font-bold">Cipher Suite:</span>
                  <span className="text-cyan-400 font-bold">
                    {lastSentResponse.payload.cipher} / {lastSentResponse.payload.kdf}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-slate-900">
                  <span className="text-slate-500 text-[10px] uppercase font-bold">Ephemeral Pub (X25519):</span>
                  <span className="text-slate-300 truncate max-w-[200px]" title={lastSentResponse.payload.ephemeral_public_key}>
                    {lastSentResponse.payload.ephemeral_public_key.slice(0, 20)}...
                  </span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-slate-900">
                  <span className="text-slate-500 text-[10px] uppercase font-bold">Ciphertext + Tag:</span>
                  <span className="text-amber-400 font-bold truncate max-w-[200px]" title={lastSentResponse.payload.ciphertext}>
                    {lastSentResponse.payload.ciphertext.slice(0, 24)}... ({lastSentResponse.payload.ciphertext.length}B)
                  </span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-slate-500 text-[10px] uppercase font-bold">Ed25519 Signature:</span>
                  <span className="text-emerald-400 font-bold truncate max-w-[200px]" title={lastSentResponse.payload.signature}>
                    {lastSentResponse.payload.signature.slice(0, 24)}... (64B)
                  </span>
                </div>
              </div>

              {/* Attack Sandbox Controls */}
              <div className="pt-3 border-t border-slate-800/60 flex gap-3">
                <button
                  type="button"
                  onClick={handleTestTamperDefense}
                  disabled={tampering}
                  className="flex-1 py-2 px-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50"
                >
                  ⚡ Test Tamper Defense
                </button>
                <button
                  type="button"
                  onClick={handleTestReplayDefense}
                  disabled={tampering}
                  className="flex-1 py-2 px-3 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50"
                >
                  ⚡ Test Replay Defense
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* COLUMN 2: RECIPIENT INBOX & DECRYPTION GATE (6 cols)              */}
        {/* ================================================================= */}
        <div className="xl:col-span-6 space-y-6">
          {/* Recipient Inbox Card */}
          <div className="glass-card rounded-2xl border border-slate-800/60 p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800/60 mb-4">
              <SectionHeader title="Recipient Device Inbox" accentColor="bg-cyan-500" className="mb-0" />
              <div className="flex items-center gap-2">
                <select
                  value={inspectDeviceId}
                  onChange={(e) => setInspectDeviceId(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-200 outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value="">Select Inspect Device...</option>
                  {members.map((m) => (
                    <option key={m.rescue_id} value={m.rescue_id}>
                      {m.name} ({m.rescue_id})
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => inspectDeviceId && loadInbox(inspectDeviceId)}
                  className="p-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 text-slate-400 hover:text-slate-200 rounded-xl transition-all cursor-pointer"
                  title="Reload Inbox"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingInbox ? 'animate-spin text-indigo-400' : ''}`} />
                </button>
              </div>
            </div>

            {loadingInbox ? (
              <div className="py-8 text-center text-slate-500 text-xs font-mono animate-pulse">
                Loading device inbox...
              </div>
            ) : inboxMessages.length === 0 ? (
              <div className="py-8 text-center text-slate-500 space-y-2 bg-slate-950/40 rounded-xl border border-slate-900">
                <FileText className="w-6 h-6 mx-auto text-slate-600" />
                <p className="text-xs">No incoming packets in this device's inbox.</p>
              </div>
            ) : (
              <div className="overflow-x-auto border border-slate-900 rounded-xl max-h-[260px] overflow-y-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-900/80 sticky top-0 border-b border-slate-800">
                    <tr>
                      <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Packet</th>
                      <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Sender</th>
                      <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Time</th>
                      <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 font-mono">
                    {inboxMessages.map((msg) => (
                      <tr key={msg.packet_id} className="hover:bg-slate-850/40">
                        <td className="px-3 py-2 text-indigo-400 font-bold">{msg.packet_id.slice(0, 8)}...</td>
                        <td className="px-3 py-2 text-slate-300">{msg.sender_rescue_id || msg.sender_device_id}</td>
                        <td className="px-3 py-2 text-slate-500 text-[10px]">
                          {msg.timestamp ? new Date(msg.timestamp * 1000).toLocaleTimeString() : 'N/A'}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <button
                            type="button"
                            onClick={() => handleDecryptInboxMessage(msg.packet_id)}
                            disabled={decryptingPacketId === msg.packet_id}
                            className="px-2.5 py-1 bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50 inline-flex items-center gap-1"
                          >
                            <Unlock className="w-3 h-3" />
                            {decryptingPacketId === msg.packet_id ? 'Decrypting...' : 'Decrypt'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Controlled Decryption Gate Inspector Card */}
          <div className="glass-card rounded-2xl border border-slate-800/60 p-6 space-y-4">
            <SectionHeader title="Decryption Gate Security Inspector" accentColor="bg-emerald-500" />

            {decryptError && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl space-y-2 animate-shake">
                <div className="flex items-center gap-2 text-red-400 font-bold text-xs uppercase tracking-wider">
                  <ShieldAlert className="w-4 h-4 text-red-500" />
                  <span>Decryption Gate: Access Denied / Security Violation</span>
                </div>
                <p className="text-xs text-red-300 font-mono">{decryptError}</p>
              </div>
            )}

            {decryptionResult ? (
              <div className="space-y-4 animate-fade-in">
                {/* Security Checks Row */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-center">
                    <span className="text-[9px] uppercase font-bold text-slate-500 block">Sender Auth</span>
                    <span className={`text-xs font-mono font-bold ${
                      decryptionResult.reason === 'UNKNOWN_SENDER' || decryptionResult.reason === 'SENDER_REVOKED' || decryptionResult.reason === 'SENDER_INACTIVE'
                        ? 'text-red-400'
                        : 'text-emerald-400'
                    }`}>
                      {decryptionResult.reason === 'UNKNOWN_SENDER'
                        ? '✗ UNKNOWN'
                        : decryptionResult.reason === 'SENDER_REVOKED'
                        ? '✗ REVOKED'
                        : decryptionResult.reason === 'SENDER_INACTIVE'
                        ? '✗ INACTIVE'
                        : '✓ VERIFIED'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-center">
                    <span className="text-[9px] uppercase font-bold text-slate-500 block">Signature</span>
                    <span className={`text-xs font-mono font-bold ${
                      decryptionResult.reason === 'INVALID_SIGNATURE'
                        ? 'text-red-400'
                        : decryptionResult.status === 'SUCCESS'
                        ? 'text-emerald-400'
                        : 'text-slate-500'
                    }`}>
                      {decryptionResult.reason === 'INVALID_SIGNATURE'
                        ? '✗ INVALID'
                        : decryptionResult.status === 'SUCCESS'
                        ? '✓ ED25519 VALID'
                        : '— SKIPPED'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-center">
                    <span className="text-[9px] uppercase font-bold text-slate-500 block">Recipient Auth</span>
                    <span className={`text-xs font-mono font-bold ${
                      decryptionResult.reason === 'UNAUTHORIZED_RECIPIENT'
                        ? 'text-red-400'
                        : decryptionResult.status === 'SUCCESS'
                        ? 'text-emerald-400'
                        : 'text-slate-500'
                    }`}>
                      {decryptionResult.reason === 'UNAUTHORIZED_RECIPIENT'
                        ? '✗ NOT AUTHORIZED'
                        : decryptionResult.status === 'SUCCESS'
                        ? '✓ AUTHORIZED'
                        : '— SKIPPED'}
                    </span>
                  </div>
                </div>

                {/* Plaintext Box (SUCCESS) or Access Denied Box (REJECTED) */}
                {decryptionResult.status === 'SUCCESS' ? (
                  <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 space-y-1.5">
                    <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block">
                      Decrypted Plaintext Emergency Message:
                    </span>
                    <p className="text-sm font-semibold text-slate-100 leading-relaxed font-sans">
                      "{decryptionResult.message}"
                    </p>
                  </div>
                ) : (
                  <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 space-y-1.5 animate-shake">
                    <div className="flex items-center gap-2 text-red-400 font-bold text-xs uppercase tracking-wider">
                      <ShieldAlert className="w-4 h-4 text-red-500" />
                      <span>Access Denied: {decryptionResult.detail || decryptionResult.reason}</span>
                    </div>
                    <p className="text-xs text-red-300 font-sans leading-relaxed">
                      The Phase 6 Decryption Gate rejected plaintext release because the security verification order failed at: <strong>{decryptionResult.reason}</strong>. Zero plaintext or private keys were leaked.
                    </p>
                  </div>
                )}

                {/* Metadata details */}
                <div className="text-[11px] font-mono text-slate-400 space-y-1 bg-slate-950/60 p-3 rounded-xl border border-slate-900">
                  <div><strong>Sender:</strong> {decryptionResult.sender_name || 'N/A'} ({decryptionResult.sender_id || 'N/A'})</div>
                  <div><strong>Packet ID:</strong> {decryptionResult.packet_id || 'N/A'}</div>
                  <div><strong>Status:</strong> <span className={decryptionResult.status === 'SUCCESS' ? 'text-emerald-400' : 'text-red-400 font-bold'}>{decryptionResult.status}</span></div>
                  {decryptionResult.detail && (
                    <div className="text-amber-400"><strong>Security Decision:</strong> {decryptionResult.detail}</div>
                  )}
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-slate-500 space-y-2 bg-slate-950/40 rounded-xl border border-slate-900">
                <ShieldCheck className="w-6 h-6 mx-auto text-slate-600" />
                <p className="text-xs">
                  Select a message from the inbox above and click <strong>Decrypt</strong> to execute the cryptographic authorization gate.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
};

