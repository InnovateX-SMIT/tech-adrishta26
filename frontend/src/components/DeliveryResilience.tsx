import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  Shield,
  Radio,
  RefreshCw,
  GitFork,
  Package,
} from 'lucide-react';
import { apiService } from '../services/api';
import type { DashboardOverviewResponse, RescueMember } from '../types';

interface DeliveryResilienceProps {
  members: RescueMember[];
  onNavigateToMessages?: () => void;
}

interface DeliveryEvent {
  id: string;
  time: string;
  type: 'info' | 'reroute' | 'queue' | 'recovered' | 'duplicate';
  message: string;
  detail: string;
}

export const DeliveryResilience: React.FC<DeliveryResilienceProps> = ({
  members: _members,
}) => {
  const [overview, setOverview] = useState<DashboardOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [statusFeedback, setStatusFeedback] = useState<{ text: string; success: boolean } | null>(null);
  const [filter, setFilter] = useState<'all' | 'failed' | 'delivered'>('all');

  const [deliveryEvents, setDeliveryEvents] = useState<DeliveryEvent[]>([
    {
      id: 'evt-1',
      time: 'Just now',
      type: 'info',
      message: 'Network route verified',
      detail: 'Multi-hop BFS path established between active rescue nodes.',
    },
    {
      id: 'evt-2',
      time: '2m ago',
      type: 'reroute',
      message: 'Another route was found.',
      detail: 'A relay device experienced latency; packet automatically rerouted via alternate path.',
    },
    {
      id: 'evt-3',
      time: '5m ago',
      type: 'queue',
      message: 'The encrypted message is waiting for a connection.',
      detail: 'Destination node temporarily out of range. Ciphertext safely queued without plaintext exposure.',
    },
    {
      id: 'evt-4',
      time: '8m ago',
      type: 'recovered',
      message: 'The message was delivered after the network recovered.',
      detail: 'Link restored; retried packet authenticated and released to authorized receiver.',
    },
    {
      id: 'evt-5',
      time: '12m ago',
      type: 'duplicate',
      message: 'A duplicate packet was ignored.',
      detail: 'Idempotency filter dropped redundant transmission, preventing replay.',
    },
  ]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiService.getDashboardOverview();
      setOverview(data);
    } catch {
      // Keep existing data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 8000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleRetry = async (messageId: string) => {
    setRetryingId(messageId);
    setStatusFeedback(null);
    try {
      await apiService.retryMessage(messageId);
      setStatusFeedback({
        text: 'The message was delivered after the network recovered.',
        success: true,
      });
      setDeliveryEvents((prev) => [
        {
          id: `evt-${Date.now()}`,
          time: 'Just now',
          type: 'recovered',
          message: 'The message was delivered after the network recovered.',
          detail: `Message ${messageId} retried successfully and verified by recipient.`,
        },
        ...prev,
      ]);
      await loadData();
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Retry failed';
      setStatusFeedback({
        text: errorMsg.includes('route')
          ? 'The original route was unavailable. Ciphertext placed in waiting state.'
          : errorMsg.includes('duplicate') || errorMsg.includes('delivered')
          ? 'A duplicate packet was ignored.'
          : `Retry result: ${errorMsg}`,
        success: false,
      });
    } finally {
      setRetryingId(null);
    }
  };

  const recentMsgs = overview?.messaging?.recent_messages || [];
  const filteredMsgs = recentMsgs.filter((m: any) => {
    if (filter === 'failed') return m.status === 'FAILED' || m.status === 'QUEUED';
    if (filter === 'delivered') return m.status === 'DELIVERED' || m.status === 'DECRYPTED';
    return true;
  });

  return (
    <div className="space-y-6 animate-fade-in select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/70 pb-5">
        <div className="flex items-center gap-3.5">
          <div className="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-black text-slate-100 uppercase tracking-tight">
                Message Delivery &amp; Reliability
              </h1>
              <span className="px-2.5 py-0.5 text-[9px] font-black uppercase tracking-widest bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                Live Telemetry
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              Real-time delivery status, alternative route selection, offline queue recovery, and duplicate prevention.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={loadData}
          disabled={loading}
          className="px-4 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-slate-100 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1.5 self-start sm:self-auto disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-indigo-400 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Refreshing...' : 'Refresh Status'}
        </button>
      </div>

      {statusFeedback && (
        <div
          className={`flex items-center gap-2.5 p-3.5 rounded-xl text-xs font-medium border ${
            statusFeedback.success
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
              : 'bg-amber-500/10 border-amber-500/20 text-amber-300'
          }`}
        >
          {statusFeedback.success ? (
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
          )}
          <span>{statusFeedback.text}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">Total Dispatches</span>
            <Package className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-2xl font-black text-slate-100">{overview?.messaging?.total_messages ?? 0}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Persistent mesh transmissions</p>
        </div>

        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Delivered</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-black text-emerald-300">{overview?.messaging?.delivered_count ?? 0}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Confirmed received by target</p>
        </div>

        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Waiting / Queued</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-black text-amber-300">
            {(overview?.messaging?.in_transit_count ?? 0) + (overview?.messaging?.failed_count ?? 0)}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Awaiting network recovery</p>
        </div>

        <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Reliability Mode</span>
            <Shield className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-black text-cyan-300">Zero-Loss</p>
          <p className="text-[11px] text-slate-400 mt-0.5">No plaintext in retry records</p>
        </div>
      </div>

      {/* Main Grid: Message Feed & Delivery Event Timeline */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left 2 Cols: Message Feed */}
        <div className="xl:col-span-2 space-y-4">
          <div className="glass-card rounded-2xl border border-slate-800/60 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
              <div>
                <h2 className="text-sm font-black text-slate-100 uppercase tracking-tight flex items-center gap-2">
                  <Radio className="w-4 h-4 text-indigo-400" />
                  Live Message Transmissions
                </h2>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Track delivery states, hop sequences, and trigger retries on disconnected packets.
                </p>
              </div>

              {/* Filters */}
              <div className="flex items-center gap-1.5 p-1 bg-slate-900 border border-slate-800 rounded-xl text-[10px] font-bold uppercase">
                <button
                  type="button"
                  onClick={() => setFilter('all')}
                  className={`px-2.5 py-1 rounded-lg transition-colors ${
                    filter === 'all' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  All ({recentMsgs.length})
                </button>
                <button
                  type="button"
                  onClick={() => setFilter('delivered')}
                  className={`px-2.5 py-1 rounded-lg transition-colors ${
                    filter === 'delivered' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Delivered
                </button>
                <button
                  type="button"
                  onClick={() => setFilter('failed')}
                  className={`px-2.5 py-1 rounded-lg transition-colors ${
                    filter === 'failed' ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Needs Retry
                </button>
              </div>
            </div>

            {/* List */}
            {filteredMsgs.length === 0 ? (
              <div className="text-center py-12 text-slate-500 font-sans space-y-2">
                <Package className="w-8 h-8 mx-auto text-slate-600 opacity-60" />
                <p className="text-xs">No messages match this filter.</p>
                <p className="text-[11px] text-slate-600">Send an emergency message from the Messages tab to observe delivery.</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
                {filteredMsgs.map((msg: any) => {
                  const isDelivered = msg.status === 'DELIVERED' || msg.status === 'DECRYPTED';
                  const isFailed = msg.status === 'FAILED' || msg.status === 'QUEUED';
                  const isRetrying = retryingId === msg.message_id;

                  return (
                    <div
                      key={msg.message_id}
                      className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 hover:border-slate-700/80 transition-all space-y-2.5"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border ${
                              isDelivered
                                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                            }`}
                          >
                            {isDelivered ? 'Delivered' : isFailed ? 'Waiting / Outage' : msg.status}
                          </span>
                          <span className="font-mono text-xs font-bold text-slate-200">{msg.message_id}</span>
                          <span className="text-[10px] text-slate-500 font-mono hidden sm:inline">
                            (Packet: {msg.packet_id})
                          </span>
                        </div>

                        {isFailed && (
                          <button
                            type="button"
                            onClick={() => handleRetry(msg.message_id)}
                            disabled={isRetrying}
                            className="px-3 py-1 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                          >
                            <RotateCcw className={`w-3 h-3 ${isRetrying ? 'animate-spin' : ''}`} />
                            {isRetrying ? 'Retrying...' : 'Retry Delivery'}
                          </button>
                        )}
                      </div>

                      {/* Routing info */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] text-slate-400 bg-slate-950/60 p-2.5 rounded-lg border border-slate-900 font-mono">
                        <div>
                          <span className="text-slate-500">From: </span>
                          <span className="text-indigo-300 font-bold">{msg.sender_device_id}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">To: </span>
                          <span className="text-indigo-300 font-bold">{msg.recipient_device_id}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Retries: </span>
                          <span className={msg.retry_count > 0 ? 'text-amber-400 font-bold' : 'text-slate-400'}>
                            {msg.retry_count || 0}
                          </span>
                        </div>
                      </div>

                      {/* Route hops preview */}
                      {msg.route && msg.route.length > 0 && (
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-400 overflow-x-auto py-0.5">
                          <span className="text-slate-500 shrink-0">Path:</span>
                          {msg.route.map((node: string, idx: number) => (
                            <React.Fragment key={idx}>
                              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono font-bold">
                                {node}
                              </span>
                              {idx < msg.route.length - 1 && (
                                <ArrowRight className="w-2.5 h-2.5 text-slate-600 shrink-0" />
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      )}

                      {/* Failure explanation */}
                      {msg.failure_reason && (
                        <p className="text-[11px] text-amber-400/90 font-medium">
                          Status note: The original route was unavailable ({msg.failure_reason}). Encrypted message queued safely.
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Delivery Events & Guarantees */}
        <div className="space-y-4">
          {/* Resilience Events Feed */}
          <div className="glass-card rounded-2xl border border-slate-800/60 p-5 space-y-3">
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <GitFork className="w-4 h-4 text-cyan-400" />
              Delivery Events Log
            </h3>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Human-readable delivery updates from the simulated mesh network routing engine.
            </p>

            <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
              {deliveryEvents.map((evt) => (
                <div
                  key={evt.id}
                  className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/60 space-y-1 text-xs"
                >
                  <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                    <span className="font-bold text-slate-300">{evt.message}</span>
                    <span>{evt.time}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">{evt.detail}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Guaranteed Security Card */}
          <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-5 space-y-2.5">
            <div className="flex items-center gap-2 text-indigo-300 font-bold text-xs uppercase tracking-wider">
              <Shield className="w-4 h-4 text-indigo-400" />
              Security After Retry Guarantee
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Every retried transmission preserves confidentiality:
            </p>
            <ul className="text-[11px] text-slate-400 space-y-1.5 list-disc pl-4 leading-relaxed">
              <li>Queued messages contain <strong className="text-slate-200">zero plaintext</strong> on disk or wire.</li>
              <li>A fresh packet ID and signature timestamp are generated on each retry.</li>
              <li>The recipient validates the sender and digital signature before releasing message content.</li>
              <li>Delivered messages cannot be redelivered or replayed.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
