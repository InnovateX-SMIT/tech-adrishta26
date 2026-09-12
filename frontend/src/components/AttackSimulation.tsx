import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import {
  CapturedPacket,
  RescueMember,
  SimulateAttackResponse,
  SimulationMode,
  TamperCaptureResponse,
} from '../types';
import {
  ShieldAlert,
  ShieldCheck,
  Radio,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Unlock,
  RotateCcw,
  ArrowRight,
  Zap,
  Activity,
} from 'lucide-react';

const PRESET_MESSAGES = [
  'SOS: Three people are trapped in Building B. Immediate evacuation required.',
  'MAYDAY: Structural collapse at Sector 7-G. 4 casualties. Need medical transport.',
  'CONFIDENTIAL DISPATCH: Evacuation corridor Charlie open. Grid 44-N, 12-E.',
];

export const AttackSimulation: React.FC = () => {
  // Configuration states
  const [mode, setMode] = useState<SimulationMode>('protected');
  const [senderId, setSenderId] = useState<string>('RESQ-001');
  const [recipientId, setRecipientId] = useState<string>('RESQ-002');
  const [message, setMessage] = useState<string>(PRESET_MESSAGES[0]);
  const [members, setMembers] = useState<RescueMember[]>([]);

  // Simulation execution states
  const [simulating, setSimulating] = useState<boolean>(false);
  const [lastResponse, setLastResponse] = useState<SimulateAttackResponse | null>(null);
  const [captures, setCaptures] = useState<CapturedPacket[]>([]);
  const [tampering, setTampering] = useState<boolean>(false);
  const [tamperResult, setTamperResult] = useState<TamperCaptureResponse | null>(null);
  const [resetting, setResetting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadInitialData = useCallback(async () => {
    try {
      const [memberList, captureList] = await Promise.all([
        apiService.fetchMembers(),
        apiService.fetchCaptures().catch(() => []),
      ]);
      setMembers(memberList);
      setCaptures(captureList);
      if (memberList.length >= 2) {
        setSenderId(memberList[0].rescue_id);
        setRecipientId(memberList[1].rescue_id);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  const handleSimulate = async () => {
    if (!message.trim()) {
      setError('Please enter an emergency distress message.');
      return;
    }
    setError(null);
    setTamperResult(null);
    setSimulating(true);

    try {
      const response = await apiService.simulateAttack({
        mode,
        sender_id: senderId,
        recipient_id: recipientId,
        message: message.trim(),
      });
      setLastResponse(response);
      const updatedCaptures = await apiService.fetchCaptures();
      setCaptures(updatedCaptures);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to run attack simulation.');
      }
    } finally {
      setSimulating(false);
    }
  };

  const handleTamper = async () => {
    if (!lastResponse?.captured_packet) return;
    setTampering(true);
    setError(null);

    try {
      const res = await apiService.tamperCapture(lastResponse.captured_packet.capture_id, {
        capture_id: lastResponse.captured_packet.capture_id,
        tamper_field: 'ciphertext',
        recipient_id: recipientId,
      });
      setTamperResult(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setTampering(false);
    }
  };

  const handleReset = async () => {
    setResetting(true);
    setError(null);
    try {
      await apiService.resetAttackSimulation();
      setLastResponse(null);
      setTamperResult(null);
      setCaptures([]);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setResetting(false);
    }
  };

  const captured = lastResponse?.captured_packet;
  const isVulnerable = mode === 'vulnerable';

  return (
    <div className="space-y-8 animate-fadeIn pb-12">
      {/* 1. Header Banner */}
      <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-wider uppercase bg-rose-500/10 text-rose-400 border border-rose-500/20 mb-3">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              Phase 7 — Packet-Sniffing Attack Simulation & Contrast Mode
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-slate-100 tracking-tight">
              Eavesdropping & Confidentiality Contrast
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Demonstrating the exact vulnerability RESQ solves: unencrypted mesh transmissions allow
              adversaries to read life-critical communications, while RESQ's cryptographic pipeline ensures
              an attacker captures only unintelligible ciphertext.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-mono px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-slate-300">
              Captured Packets: <strong className="text-cyan-400">{captures.length}</strong>
            </span>
            <button
              onClick={handleReset}
              disabled={resetting}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800/80 hover:bg-slate-750 text-slate-300 hover:text-white rounded-xl border border-slate-700 text-xs font-medium transition-all shadow-sm self-start md:self-auto disabled:opacity-50"
              title="Clears Phase 7 simulation captures while preserving registry identities and keys"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`} />
              {resetting ? 'Resetting...' : 'Reset Simulation'}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/40 border border-rose-500/30 rounded-xl p-4 flex items-center gap-3 text-rose-200 text-sm">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 2. Simulation Mode Selector */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mode A: Vulnerable */}
        <div
          onClick={() => setMode('vulnerable')}
          className={`cursor-pointer rounded-2xl p-5 border transition-all relative overflow-hidden ${
            isVulnerable
              ? 'bg-rose-950/20 border-rose-500/50 shadow-lg shadow-rose-950/30 ring-1 ring-rose-500/30'
              : 'bg-slate-900/40 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60'
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`p-2.5 rounded-xl ${
                  isVulnerable ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-slate-800 text-slate-400'
                }`}
              >
                <Unlock className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-100 text-base flex items-center gap-2">
                  Before RESQ — Vulnerable Mode
                  {isVulnerable && (
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                      Active
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Unencrypted mesh broadcast simulation</p>
              </div>
            </div>
            <div
              className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                isVulnerable ? 'border-rose-400 bg-rose-400' : 'border-slate-600'
              }`}
            >
              {isVulnerable && <div className="w-1.5 h-1.5 rounded-full bg-slate-950" />}
            </div>
          </div>

          <p className="text-xs text-slate-300 mt-4 leading-relaxed">
            Messages are sent without encryption. An eavesdropping packet sniffer in range captures the
            packet and <strong className="text-rose-400 font-semibold">directly reads the distress message</strong>.
          </p>

          <div className="mt-4 pt-3 border-t border-slate-800/60 flex flex-wrap gap-2 text-[11px]">
            <span className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700">
              Encryption: None
            </span>
            <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
              Attacker Readable: Yes
            </span>
            <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
              Exposure: High Risk
            </span>
          </div>
        </div>

        {/* Mode B: Protected */}
        <div
          onClick={() => setMode('protected')}
          className={`cursor-pointer rounded-2xl p-5 border transition-all relative overflow-hidden ${
            !isVulnerable
              ? 'bg-emerald-950/20 border-emerald-500/50 shadow-lg shadow-emerald-950/30 ring-1 ring-emerald-500/30'
              : 'bg-slate-900/40 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60'
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`p-2.5 rounded-xl ${
                  !isVulnerable ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
                }`}
              >
                <Lock className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-100 text-base flex items-center gap-2">
                  After RESQ — Protected Mode
                  {!isVulnerable && (
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      Active
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">X25519 + ChaCha20-Poly1305 + Ed25519</p>
              </div>
            </div>
            <div
              className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                !isVulnerable ? 'border-emerald-400 bg-emerald-400' : 'border-slate-600'
              }`}
            >
              {!isVulnerable && <div className="w-1.5 h-1.5 rounded-full bg-slate-950" />}
            </div>
          </div>

          <p className="text-xs text-slate-300 mt-4 leading-relaxed">
            Messages are encrypted and signed before transmission. An eavesdropper captures the packet but{' '}
            <strong className="text-emerald-400 font-semibold">sees only unintelligible ciphertext</strong>.
          </p>

          <div className="mt-4 pt-3 border-t border-slate-800/60 flex flex-wrap gap-2 text-[11px]">
            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Encryption: ChaCha20-Poly1305
            </span>
            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Attacker Readable: No
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700">
              Signature: Ed25519
            </span>
          </div>
        </div>
      </div>

      {/* 3. Message Composer & Simulation Trigger */}
      <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
              <Radio className="w-5 h-5 text-cyan-400" />
              Emergency Distress Message Composer
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Select verified devices and transmit across the simulated mesh network.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">
            Current Mode: <span className={isVulnerable ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'}>{mode.toUpperCase()}</span>
          </span>
        </div>

        {/* Sender & Recipient Pickers */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Sender (Distress Origin)
            </label>
            <select
              value={senderId}
              onChange={(e) => setSenderId(e.target.value)}
              className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
            >
              {members.map((m) => (
                <option key={m.rescue_id} value={m.rescue_id}>
                  {m.name} ({m.rescue_id} — {m.team})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Recipient (Rescue Base)
            </label>
            <select
              value={recipientId}
              onChange={(e) => setRecipientId(e.target.value)}
              className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
            >
              {members
                .filter((m) => m.rescue_id !== senderId)
                .map((m) => (
                  <option key={m.rescue_id} value={m.rescue_id}>
                    {m.name} ({m.rescue_id} — {m.team})
                  </option>
                ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Eavesdropping Sniffer Node
            </label>
            <div className="w-full bg-slate-800/50 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-rose-300 flex items-center justify-between">
              <span className="flex items-center gap-1.5 font-mono">
                <Eye className="w-3.5 h-3.5 text-rose-400" />
                DEVICE-004 (Sniffer Tap)
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 uppercase font-semibold">
                Listening
              </span>
            </div>
          </div>
        </div>

        {/* Message Input & Presets */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-medium text-slate-300">
              Distress Message Content
            </label>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-slate-500 hidden sm:inline">Presets:</span>
              {PRESET_MESSAGES.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setMessage(preset)}
                  className="text-[10px] px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition-colors"
                >
                  Preset #{idx + 1}
                </button>
              ))}
            </div>
          </div>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
            className="w-full bg-slate-800/90 border border-slate-700 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 font-sans"
            placeholder="Type emergency distress dispatch..."
          />
        </div>

        {/* Action Button */}
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-slate-400">
            {isVulnerable ? (
              <span className="text-rose-400">
                Warning: Will transmit unencrypted. Attacker will intercept in plaintext.
              </span>
            ) : (
              <span className="text-emerald-400">
                Protected: Will encrypt with ChaCha20-Poly1305 and sign with Ed25519.
              </span>
            )}
          </p>

          <button
            onClick={handleSimulate}
            disabled={simulating}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium text-xs shadow-lg transition-all disabled:opacity-50 ${
              isVulnerable
                ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/30'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-900/30'
            }`}
          >
            {simulating ? (
              <>
                <Activity className="w-4 h-4 animate-spin" />
                <span>Simulating Mesh Transit...</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                <span>Run Attack Simulation ({mode.toUpperCase()})</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 4. Live Simulation Results Display */}
      {lastResponse && captured && (
        <div className="space-y-6">
          {/* Main Key Takeaway Banner */}
          <div
            className={`p-4 rounded-2xl border flex items-center gap-4 ${
              isVulnerable
                ? 'bg-rose-950/30 border-rose-500/40 text-rose-200'
                : 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
            }`}
          >
            <div
              className={`p-3 rounded-xl shrink-0 ${
                isVulnerable ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'
              }`}
            >
              {isVulnerable ? <Eye className="w-6 h-6" /> : <ShieldCheck className="w-6 h-6" />}
            </div>
            <div>
              <h4 className="text-sm font-semibold tracking-tight">
                {lastResponse.summary_sentence}
              </h4>
              <p className="text-xs opacity-90 mt-0.5">{captured.explanation}</p>
            </div>
          </div>

          {/* Mesh Route Traversal Visualizer */}
          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-2xl p-5 shadow-xl">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              Mesh Transit Path & Sniffing Tap Point
            </h3>

            <div className="flex flex-wrap items-center gap-2 lg:gap-4 py-2">
              {lastResponse.route.map((nodeId, idx) => {
                const isAttackerNode = nodeId.includes('004') || nodeId.includes('ATTACKER') || nodeId.includes('NODE-D');
                const isOrigin = idx === 0;
                const isDestination = idx === lastResponse.route.length - 1;

                return (
                  <React.Fragment key={nodeId}>
                    <div
                      className={`px-3 py-2 rounded-xl border text-xs font-mono flex items-center gap-2 ${
                        isAttackerNode
                          ? 'bg-rose-950/40 border-rose-500/40 text-rose-300 shadow-md shadow-rose-950/40'
                          : isOrigin || isDestination
                          ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-300'
                          : 'bg-slate-800 border-slate-700 text-slate-300'
                      }`}
                    >
                      {isAttackerNode && <Eye className="w-3.5 h-3.5 text-rose-400 animate-pulse" />}
                      <span>{nodeId}</span>
                      {isAttackerNode && (
                        <span className="text-[9px] px-1 rounded bg-rose-500/30 text-rose-200 uppercase font-bold">
                          Sniffer Tap
                        </span>
                      )}
                      {isOrigin && (
                        <span className="text-[9px] px-1 rounded bg-cyan-500/30 text-cyan-200 uppercase font-bold">
                          Origin
                        </span>
                      )}
                      {isDestination && (
                        <span className="text-[9px] px-1 rounded bg-emerald-500/30 text-emerald-200 uppercase font-bold">
                          Dest
                        </span>
                      )}
                    </div>
                    {idx < lastResponse.route.length - 1 && (
                      <ArrowRight className="w-4 h-4 text-slate-600 shrink-0" />
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* Two-Column Side-by-Side: Attacker View vs. Receiver View */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: What the Attacker Sniffed */}
            <div
              className={`rounded-2xl border p-5 backdrop-blur-md shadow-xl flex flex-col justify-between ${
                isVulnerable
                  ? 'bg-rose-950/20 border-rose-500/40 shadow-rose-950/20'
                  : 'bg-slate-900/60 border-slate-800'
              }`}
            >
              <div>
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-4">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`p-2 rounded-lg ${
                        isVulnerable ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {isVulnerable ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100">
                        Attacker Inspection Panel
                      </h3>
                      <p className="text-[11px] text-slate-400">Captured at {captured.captured_at_node}</p>
                    </div>
                  </div>

                  <span
                    className={`text-[11px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider border ${
                      captured.message_readable_by_attacker
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                        : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    }`}
                  >
                    Readable: {captured.message_readable_by_attacker ? 'YES (EXPOSED)' : 'NO (PROTECTED)'}
                  </span>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-2 text-slate-400">
                    <div>
                      <span className="text-slate-500 block text-[10px]">Capture ID:</span>
                      <span className="font-mono text-slate-200">{captured.capture_id}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Packet ID:</span>
                      <span className="font-mono text-slate-200">{captured.packet_id}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Sender Claim:</span>
                      <span className="font-mono text-slate-200">{captured.sender_id}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Target Recipient:</span>
                      <span className="font-mono text-slate-200">{captured.recipient_id}</span>
                    </div>
                  </div>

                  {/* Metadata visibility note */}
                  <div className="p-2.5 rounded-xl bg-slate-800/40 border border-slate-700/60 text-[11px] text-slate-300">
                    <span className="text-slate-400 block font-medium mb-0.5">
                      Routing Metadata Notice:
                    </span>
                    Headers (sender/recipient IDs, packet size) are visible to transport observers. Encryption
                    protects message contents from disclosure.
                  </div>

                  {/* Sniffed Content Box */}
                  <div>
                    <span className="text-slate-400 block text-[11px] font-medium mb-1.5">
                      Sniffed Packet Contents:
                    </span>
                    <div
                      className={`p-3 rounded-xl font-mono text-xs break-all border ${
                        isVulnerable
                          ? 'bg-rose-950/40 text-rose-200 border-rose-500/40 shadow-inner'
                          : 'bg-slate-950 text-slate-300 border-slate-800'
                      }`}
                    >
                      {captured.sniffed_content}
                    </div>
                  </div>
                </div>
              </div>

              {/* Tamper Button if in Protected Mode */}
              {!isVulnerable && (
                <div className="mt-5 pt-4 border-t border-slate-800/80">
                  <button
                    onClick={handleTamper}
                    disabled={tampering}
                    className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-medium transition-colors disabled:opacity-50"
                  >
                    <Zap className="w-3.5 h-3.5" />
                    {tampering ? 'Tampering with Packet...' : 'Test Tampering Defense (Alter 1 Byte)'}
                  </button>

                  {tamperResult && (
                    <div className="mt-3 p-3 rounded-xl bg-amber-950/30 border border-amber-500/30 text-xs text-amber-200 space-y-1">
                      <div className="flex items-center justify-between font-semibold text-[11px]">
                        <span>Receiver Gate Decision:</span>
                        <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                          {tamperResult.receiver_status}
                        </span>
                      </div>
                      <p className="text-[11px] opacity-90">{tamperResult.explanation}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right: What the Authorized Receiver Sees */}
            <div
              className={`rounded-2xl border p-5 backdrop-blur-md shadow-xl flex flex-col justify-between ${
                isVulnerable
                  ? 'bg-slate-900/50 border-slate-800'
                  : 'bg-emerald-950/20 border-emerald-500/40 shadow-emerald-950/20'
              }`}
            >
              <div>
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-4">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`p-2 rounded-lg ${
                        isVulnerable ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'
                      }`}
                    >
                      {isVulnerable ? <AlertTriangle className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100">
                        Authorized Receiver Panel
                      </h3>
                      <p className="text-[11px] text-slate-400">Recipient: {recipientId}</p>
                    </div>
                  </div>

                  <span
                    className={`text-[11px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider border ${
                      !isVulnerable
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    }`}
                  >
                    {!isVulnerable ? 'Decrypted & Verified' : 'Insecure Receipt'}
                  </span>
                </div>

                <div className="space-y-3 text-xs">
                  {!isVulnerable ? (
                    <>
                      {/* Security checks checklist */}
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Sender Registry: Verified</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Sender Status: Active</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Ed25519 Signature: Valid</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Authorization: Approved</span>
                        </div>
                      </div>

                      <div>
                        <span className="text-slate-400 block text-[11px] font-medium mb-1.5">
                          Decrypted Plaintext (Authorized Receiver Only):
                        </span>
                        <div className="p-3 rounded-xl bg-emerald-950/40 text-emerald-100 border border-emerald-500/30 text-xs font-sans leading-relaxed">
                          "{String(lastResponse.receiver_result.message ?? '')}"
                        </div>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-500/30 text-amber-200 text-xs">
                        <span className="font-semibold block mb-1">Insecure Delivery Warning:</span>
                        The message arrived without cryptographic encryption or Ed25519 digital signature.
                        Any party on the mesh route had complete read and tampering access to this message.
                      </div>

                      <div>
                        <span className="text-slate-400 block text-[11px] font-medium mb-1.5">
                          Unencrypted Message Received:
                        </span>
                        <div className="p-3 rounded-xl bg-slate-950 text-slate-300 border border-slate-800 text-xs font-sans">
                          "{String(lastResponse.receiver_result.message ?? '')}"
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
                Decision: <strong className="text-slate-200">{String(lastResponse.receiver_result.status)}</strong>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

