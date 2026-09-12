import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import {
  MeshNodeInfo,
  MeshTopologyResponse,
  RouteDiscoveryResponse,
  MeshPacketResponse,
  DeliveryLogSchema,
} from '../types';
import {
  Network,
  Radio,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Search,
  Send,
  Eye,
  Activity,
  Power,
  Layers,
} from 'lucide-react';
import { SectionHeader } from './layout/SectionHeader';

interface NodeCoordinates {
  x: number;
  y: number;
}

export const MeshVisualizer: React.FC = () => {
  const [topology, setTopology] = useState<MeshTopologyResponse>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Route Discovery & Simulation state
  const [sourceNode, setSourceNode] = useState<string>('');
  const [destNode, setDestNode] = useState<string>('');
  const [ttl, setTtl] = useState<number>(10);
  const [payloadText, setPayloadText] = useState<string>('SOS: Emergency coordinates alpha-7');
  const [discoveredRoute, setDiscoveredRoute] = useState<RouteDiscoveryResponse | null>(null);
  const [lastPacket, setLastPacket] = useState<MeshPacketResponse | null>(null);
  const [simulatingHop, setSimulatingHop] = useState<number>(-1);

  // Attacker & Logs state
  const [capturedPackets, setCapturedPackets] = useState<MeshPacketResponse[]>([]);
  const [deliveryLogs, setDeliveryLogs] = useState<DeliveryLogSchema[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeInbox, setNodeInbox] = useState<MeshPacketResponse[]>([]);

  // Fixed visual coordinate mapping for standard 5-node + attacker demo topologies
  const getNodeCoordinates = useCallback((nodeId: string, index: number, total: number): NodeCoordinates => {
    const predefined: Record<string, NodeCoordinates> = {
      'NODE-A': { x: 110, y: 170 },
      'NODE-B': { x: 270, y: 170 },
      'NODE-C': { x: 430, y: 100 },
      'NODE-D': { x: 270, y: 290 },
      'NODE-E': { x: 590, y: 100 },
      'ATTACKER': { x: 430, y: 270 },
      'DEVICE-001': { x: 110, y: 170 },
      'DEVICE-002': { x: 270, y: 170 },
      'DEVICE-003': { x: 430, y: 100 },
      'DEVICE-004': { x: 270, y: 290 },
      'DEVICE-005': { x: 590, y: 100 },
    };

    if (predefined[nodeId]) {
      return predefined[nodeId];
    }

    // Dynamic circular layout fallback for custom nodes
    const angle = (index / Math.max(total, 1)) * 2 * Math.PI - Math.PI / 2;
    const centerX = 350;
    const centerY = 190;
    const radius = 140;
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  }, []);

  const refreshTopology = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.fetchMeshTopology();
      setTopology(data);

      // Auto-populate dropdowns if empty
      if (data.nodes.length >= 2) {
        setSourceNode((prev) => (prev && data.nodes.some((n) => n.node_id === prev) ? prev : data.nodes[0].node_id));
        setDestNode((prev) => (prev && data.nodes.some((n) => n.node_id === prev) ? prev : data.nodes[data.nodes.length - 1].node_id));
      }

      // Check attacker packets
      const attackerNode = data.nodes.find((n) => n.is_attacker);
      if (attackerNode) {
        try {
          const capData = await apiService.fetchAttackerCaptured(attackerNode.node_id);
          setCapturedPackets(capData.captured);
        } catch {
          // Attacker might not have packets yet
        }
      }

      // Fetch delivery logs
      try {
        const logs = await apiService.fetchMeshLogs();
        setDeliveryLogs(logs);
      } catch {
        // Safe to ignore
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch mesh topology.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshTopology();
  }, [refreshTopology]);

  // Handle building standard demo network
  const handleBuildDemo = async (useDeviceIds = false) => {
    try {
      setLoading(true);
      setError(null);
      await apiService.buildMeshDemo(useDeviceIds);
      setSuccessMsg(useDeviceIds ? 'Built demo mesh using registered DEVICE IDs.' : 'Built standard 5-node demo topology (NODE-A..E + ATTACKER).');
      setDiscoveredRoute(null);
      setLastPacket(null);
      await refreshTopology();
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err.message || 'Failed to initialize demo network.');
    } finally {
      setLoading(false);
    }
  };

  // Handle resetting mesh
  const handleReset = async () => {
    try {
      setLoading(true);
      await apiService.resetMeshNetwork();
      setTopology({ nodes: [], edges: [] });
      setDiscoveredRoute(null);
      setLastPacket(null);
      setCapturedPackets([]);
      setDeliveryLogs([]);
      setSelectedNodeId(null);
      setNodeInbox([]);
      setSuccessMsg('Mesh network has been reset.');
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to reset mesh network.');
    } finally {
      setLoading(false);
    }
  };

  // Discover route
  const handleDiscoverRoute = async () => {
    if (!sourceNode || !destNode) {
      setError('Please select both source and destination nodes.');
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const res = await apiService.findMeshRoute(sourceNode, destNode);
      setDiscoveredRoute(res);
      if (!res.reachable) {
        setError(`Route Unreachable: ${res.failure_reason || 'No path available.'}`);
      } else {
        setSuccessMsg(`Route discovered: ${res.path.join(' ➔ ')} (${res.hop_count} hops)`);
        setTimeout(() => setSuccessMsg(null), 4000);
      }
    } catch (err: any) {
      setError(err.message || 'Route discovery failed.');
      setDiscoveredRoute(null);
    } finally {
      setLoading(false);
    }
  };

  // Simulate packet transmission
  const handleSimulateTransmission = async () => {
    if (!sourceNode || !destNode) {
      setError('Please select both source and destination nodes.');
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const packet = await apiService.sendMeshPacket(sourceNode, destNode, payloadText, ttl);
      setLastPacket(packet);

      // Animate hops on visual canvas
      if (packet.hop_log && packet.hop_log.length > 0) {
        for (let i = 0; i < packet.hop_log.length; i++) {
          setSimulatingHop(i);
          await new Promise((r) => setTimeout(r, 450));
        }
        setSimulatingHop(-1);
      }

      setSuccessMsg(`Packet delivered to ${destNode} across ${packet.hop_log.length} hops.`);
      setTimeout(() => setSuccessMsg(null), 4000);

      // Refresh attacker packets and logs
      await refreshTopology();
      if (selectedNodeId === destNode) {
        inspectNode(destNode);
      }
    } catch (err: any) {
      setSimulatingHop(-1);
      setError(err.message || 'Packet forwarding failed.');
      await refreshTopology();
    } finally {
      setLoading(false);
    }
  };

  // Toggle Online/Offline state
  const handleToggleOnline = async (node: MeshNodeInfo) => {
    try {
      setError(null);
      await apiService.updateNodeState(node.node_id, { is_online: !node.is_online });
      setSuccessMsg(`Node ${node.node_id} marked ${!node.is_online ? 'ONLINE' : 'OFFLINE'}.`);
      setDiscoveredRoute(null);
      setTimeout(() => setSuccessMsg(null), 3000);
      await refreshTopology();
    } catch (err: any) {
      setError(err.message || `Failed to update node ${node.node_id}.`);
    }
  };

  // Inspect node inbox
  const inspectNode = async (nodeId: string) => {
    setSelectedNodeId(nodeId);
    try {
      const inbox = await apiService.fetchNodeInbox(nodeId);
      setNodeInbox(inbox);
    } catch {
      setNodeInbox([]);
    }
  };

  // Check if edge is in discovered route or last packet hop
  const isEdgeHighlighted = (nodeA: string, nodeB: string): boolean => {
    const route = discoveredRoute?.reachable
      ? discoveredRoute.path
      : lastPacket?.hop_log?.map((h) => h.from_node).concat(lastPacket.hop_log[lastPacket.hop_log.length - 1]?.to_node || []);

    if (!route || route.length < 2) return false;

    for (let i = 0; i < route.length - 1; i++) {
      const u = route[i];
      const v = route[i + 1];
      if ((u === nodeA && v === nodeB) || (u === nodeB && v === nodeA)) {
        return true;
      }
    }
    return false;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 border-b border-slate-800/70 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-black text-slate-100 uppercase tracking-tight">
                  Mesh Simulation Engine
                </h1>
                <span className="px-2.5 py-0.5 text-[9px] font-black uppercase tracking-widest bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded-full">
                  Mesh Relay Engine Active
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Decentralized peer-to-peer relay network simulation with BFS routing, node outage resilience, and eavesdropper detection.
              </p>
            </div>
          </div>
        </div>

        {/* Quick Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => handleBuildDemo(false)}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-slate-100 rounded-xl text-xs font-bold uppercase tracking-wider transition-all disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
          >
            <Play className="w-3.5 h-3.5 text-indigo-400" />
            Demo Mesh (A..E)
          </button>
          <button
            type="button"
            onClick={() => handleBuildDemo(true)}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-slate-100 rounded-xl text-xs font-bold uppercase tracking-wider transition-all disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
          >
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            Registered Mesh
          </button>
          <button
            type="button"
            onClick={handleReset}
            disabled={loading}
            className="px-3.5 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 hover:text-red-300 rounded-xl text-xs font-bold uppercase tracking-wider transition-all disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset Topology
          </button>
        </div>
      </div>

      {/* Alerts / Feedback */}
      {error && (
        <div className="flex items-center justify-between gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-4 animate-shake">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
            <p className="text-xs sm:text-sm text-red-400 font-medium">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-200 text-xs font-bold uppercase cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {successMsg && (
        <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 animate-fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <p className="text-xs sm:text-sm text-emerald-400 font-medium">{successMsg}</p>
        </div>
      )}

      {/* 2. Main Grid: SVG Canvas & Controls */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left Column: Interactive Topology Canvas (8 cols) */}
        <div className="xl:col-span-8 glass-card rounded-2xl border border-slate-800/60 p-6 flex flex-col justify-between min-h-[460px] relative overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-800/60">
            <SectionHeader
              title={`Topology Canvas (${topology.nodes.length} Nodes, ${topology.edges.length} Links)`}
              accentColor="bg-cyan-500"
              className="mb-0"
            />
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
              </span>
              <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase tracking-wider">
                Sim Active
              </span>
            </div>
          </div>

          {/* SVG Visualizer Canvas */}
          <div className="flex-1 flex items-center justify-center my-4 min-h-[360px] bg-slate-950/60 rounded-xl border border-slate-900 relative overflow-hidden">
            {topology.nodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center space-y-4">
                <div className="p-3 bg-slate-900 border border-slate-800 rounded-2xl text-slate-500">
                  <Network className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
                    Mesh Topology is Empty
                  </h3>
                  <p className="text-xs text-slate-500 max-w-sm mt-1">
                    Initialize the demo topology or register rescue devices to simulate peer-to-peer message forwarding.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleBuildDemo(false)}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold uppercase tracking-wider shadow-lg shadow-indigo-600/20 cursor-pointer transition-all"
                >
                  Construct 5-Node Demo Mesh
                </button>
              </div>
            ) : (
              <svg viewBox="0 0 700 360" className="w-full h-full select-none">
                <defs>
                  <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                  <filter id="glow-indigo" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                  <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                  <filter id="glow-amber" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                </defs>

                {/* Cyber Grid Background */}
                <g opacity="0.08">
                  {Array.from({ length: 15 }).map((_, i) => (
                    <line key={`gx-${i}`} x1={i * 50} y1="0" x2={i * 50} y2="360" stroke="#6366f1" strokeWidth="0.7" />
                  ))}
                  {Array.from({ length: 8 }).map((_, i) => (
                    <line key={`gy-${i}`} x1="0" y1={i * 50} x2="700" y2={i * 50} stroke="#6366f1" strokeWidth="0.7" />
                  ))}
                </g>

                {/* Edges / Peer Links */}
                {topology.edges.map(([aId, bId], idx) => {
                  const nodeAIndex = topology.nodes.findIndex((n) => n.node_id === aId);
                  const nodeBIndex = topology.nodes.findIndex((n) => n.node_id === bId);
                  const posA = getNodeCoordinates(aId, nodeAIndex, topology.nodes.length);
                  const posB = getNodeCoordinates(bId, nodeBIndex, topology.nodes.length);
                  const isHighlighted = isEdgeHighlighted(aId, bId);
                  const isAttackerAdjacent = aId === 'ATTACKER' || bId === 'ATTACKER';

                  return (
                    <line
                      key={`edge-${aId}-${bId}-${idx}`}
                      x1={posA.x}
                      y1={posA.y}
                      x2={posB.x}
                      y2={posB.y}
                      stroke={isHighlighted ? '#6366f1' : isAttackerAdjacent ? '#f59e0b' : '#1e293b'}
                      strokeWidth={isHighlighted ? 3 : isAttackerAdjacent ? 2 : 1.5}
                      strokeDasharray={isHighlighted ? '8 8' : isAttackerAdjacent ? '4 4' : undefined}
                      className={isHighlighted ? 'animate-packet-flow' : undefined}
                      filter={isHighlighted ? 'url(#glow-indigo)' : undefined}
                      strokeOpacity={isHighlighted ? 1 : isAttackerAdjacent ? 0.6 : 0.8}
                    />
                  );
                })}

                {/* Nodes */}
                {topology.nodes.map((node, idx) => {
                  const pos = getNodeCoordinates(node.node_id, idx, topology.nodes.length);
                  const isSource = node.node_id === sourceNode;
                  const isDest = node.node_id === destNode;
                  const isSelected = node.node_id === selectedNodeId;
                  const isRouteNode = discoveredRoute?.path?.includes(node.node_id);
                  const isCurrentHop = simulatingHop >= 0 && lastPacket?.hop_log?.[simulatingHop]?.to_node === node.node_id;

                  let fillColor = node.is_online ? '#0f172a' : '#270810';
                  let strokeColor = node.is_online ? '#10b981' : '#ef4444';
                  let filter = undefined;

                  if (node.is_attacker) {
                    strokeColor = '#f59e0b';
                    fillColor = '#1c1303';
                    filter = 'url(#glow-amber)';
                  } else if (isCurrentHop) {
                    strokeColor = '#ec4899';
                    fillColor = '#3b0720';
                    filter = 'url(#glow-red)';
                  } else if (isSource) {
                    strokeColor = '#6366f1';
                    filter = 'url(#glow-indigo)';
                  } else if (isDest) {
                    strokeColor = '#22d3ee';
                    filter = 'url(#glow-cyan)';
                  }

                  return (
                    <g
                      key={`node-${node.node_id}`}
                      onClick={() => inspectNode(node.node_id)}
                      className="cursor-pointer group"
                    >
                      {/* Active or Focus Ring */}
                      {(isSelected || isSource || isDest || isCurrentHop) && (
                        <circle
                          cx={pos.x}
                          cy={pos.y}
                          r={isCurrentHop ? 30 : 26}
                          fill="none"
                          stroke={isCurrentHop ? '#ec4899' : isSource ? '#6366f1' : isDest ? '#22d3ee' : '#94a3b8'}
                          strokeWidth={isCurrentHop ? 2.5 : 1.5}
                          strokeDasharray={isCurrentHop ? '3 3' : '4 2'}
                          className="transition-all"
                        />
                      )}

                      {/* Main Node Circle */}
                      <circle
                        cx={pos.x}
                        cy={pos.y}
                        r={20}
                        fill={fillColor}
                        stroke={strokeColor}
                        strokeWidth={2}
                        filter={filter}
                      />

                      {/* Live indicator dot inside top right */}
                      <circle
                        cx={pos.x + 12}
                        cy={pos.y - 12}
                        r={4}
                        fill={node.is_online ? '#10b981' : '#ef4444'}
                      />

                      {/* Node Label Text */}
                      <text
                        x={pos.x}
                        y={pos.y + 4}
                        fill="#f8fafc"
                        fontSize="9"
                        fontWeight="700"
                        textAnchor="middle"
                        fontFamily="JetBrains Mono, monospace"
                      >
                        {node.is_attacker ? 'SNIFFER' : node.node_id}
                      </text>

                      {/* Sub-label Below Node */}
                      <text
                        x={pos.x}
                        y={pos.y + 34}
                        fill={node.is_online ? '#94a3b8' : '#ef4444'}
                        fontSize="8.5"
                        fontWeight="600"
                        textAnchor="middle"
                        fontFamily="Inter, sans-serif"
                      >
                        {node.is_attacker
                          ? '⚠️ Eavesdropper'
                          : node.is_online
                          ? isSource
                            ? '● SOURCE'
                            : isDest
                            ? '● DEST'
                            : isRouteNode
                            ? '⚡ RELAY'
                            : 'ONLINE'
                          : '✕ OFFLINE'}
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>

          {/* Canvas Legend */}
          <div className="pt-3 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-4 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span>Online Relay</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
              <span>Offline (Outage)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span>Passive Sniffer</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-0.5 bg-indigo-500" />
              <span>BFS Traversal Link</span>
            </div>
          </div>
        </div>

        {/* Right Column: Route Discovery & Node Inspector (4 cols) */}
        <div className="xl:col-span-4 space-y-6">
          {/* Route Discovery Card */}
          <div className="glass-card rounded-2xl border border-slate-800/60 p-6">
            <SectionHeader title="Route & Packet Dispatch" accentColor="bg-indigo-500" />

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                    Source Node
                  </label>
                  <select
                    value={sourceNode}
                    onChange={(e) => setSourceNode(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    {topology.nodes.map((n) => (
                      <option key={`src-${n.node_id}`} value={n.node_id}>
                        {n.node_id} {!n.is_online ? '(OFFLINE)' : n.is_attacker ? '(ATTACKER)' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                    Destination Node
                  </label>
                  <select
                    value={destNode}
                    onChange={(e) => setDestNode(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    {topology.nodes.map((n) => (
                      <option key={`dst-${n.node_id}`} value={n.node_id}>
                        {n.node_id} {!n.is_online ? '(OFFLINE)' : n.is_attacker ? '(ATTACKER)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-1">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                    TTL (Hops)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="50"
                    value={ttl}
                    onChange={(e) => setTtl(parseInt(e.target.value, 10) || 10)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono font-bold text-indigo-400 outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                    Packet Payload
                  </label>
                  <input
                    type="text"
                    value={payloadText}
                    onChange={(e) => setPayloadText(e.target.value)}
                    placeholder="Enter simulation payload..."
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500 font-medium"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <button
                  type="button"
                  onClick={handleDiscoverRoute}
                  disabled={loading || !sourceNode || !destNode}
                  className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-slate-200 font-bold text-xs uppercase tracking-wider rounded-xl transition-all cursor-pointer disabled:opacity-50"
                >
                  <Search className="w-3.5 h-3.5 text-indigo-400" />
                  Discover Route
                </button>

                <button
                  type="button"
                  onClick={handleSimulateTransmission}
                  disabled={loading || !sourceNode || !destNode}
                  className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-black text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-indigo-600/10 transition-all cursor-pointer disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  Send Packet
                </button>
              </div>

              {/* Route Summary Box */}
              {discoveredRoute && (
                <div
                  className={`p-3.5 rounded-xl border text-xs ${
                    discoveredRoute.reachable
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                      : 'bg-red-500/10 border-red-500/20 text-red-400'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-extrabold uppercase tracking-wider">
                      {discoveredRoute.reachable ? '✓ Route Discovered' : '✕ Destination Unreachable'}
                    </span>
                    {discoveredRoute.reachable && (
                      <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-bold text-[10px]">
                        {discoveredRoute.hop_count} Hops
                      </span>
                    )}
                  </div>
                  {discoveredRoute.reachable ? (
                    <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px] font-bold">
                      {discoveredRoute.path.map((node, i) => (
                        <React.Fragment key={`hop-${node}`}>
                          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-indigo-300">
                            {node}
                          </span>
                          {i < discoveredRoute.path.length - 1 && (
                            <span className="text-slate-600">➔</span>
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px] text-red-400/90 leading-relaxed font-mono">
                      {discoveredRoute.failure_reason || 'No available path due to network partitioning or node outages.'}
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Node Controller & Inspector Card */}
          <div className="glass-card rounded-2xl border border-slate-800/60 p-6">
            <SectionHeader title="Node Controller & Telemetry" accentColor="bg-cyan-500" />

            {selectedNodeId ? (
              (() => {
                const node = topology.nodes.find((n) => n.node_id === selectedNodeId);
                if (!node) return <p className="text-xs text-slate-500">Node not found.</p>;
                return (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800/60">
                      <div>
                        <h4 className="text-sm font-black text-slate-100 font-mono">
                          {node.node_id}
                        </h4>
                        <span
                          className={`inline-block mt-1 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${
                            node.is_online
                              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                              : 'bg-red-500/10 border-red-500/20 text-red-400'
                          }`}
                        >
                          {node.is_online ? 'ONLINE' : 'OFFLINE'}
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleToggleOnline(node)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1.5 ${
                          node.is_online
                            ? 'bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400'
                            : 'bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400'
                        }`}
                      >
                        <Power className="w-3.5 h-3.5" />
                        {node.is_online ? 'Simulate Outage' : 'Restore Online'}
                      </button>
                    </div>

                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between items-center py-1 border-b border-slate-900">
                        <span className="text-[10px] uppercase font-bold text-slate-500">Relay Forwarder</span>
                        <span className="font-mono font-bold text-slate-300">
                          {node.is_available_for_relay ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-1 border-b border-slate-900">
                        <span className="text-[10px] uppercase font-bold text-slate-500">Neighbors</span>
                        <span className="font-mono text-slate-300">
                          {node.neighbors.length > 0 ? node.neighbors.join(', ') : 'None'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-1">
                        <span className="text-[10px] uppercase font-bold text-slate-500">Node Inbox</span>
                        <span className="font-mono font-bold text-indigo-400">
                          {nodeInbox.length} delivered
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })()
            ) : (
              <div className="py-6 text-center text-slate-500 space-y-2">
                <Radio className="w-6 h-6 mx-auto text-slate-600 animate-pulse" />
                <p className="text-xs">
                  Click any node on the canvas to inspect its status or simulate link outages.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. Bottom Grid: Eavesdropper Sniffing Panel vs Delivery Audit Log */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
        {/* Passive Sniffer Interception Feed */}
        <div className="glass-card rounded-2xl border border-amber-500/30 p-6 relative overflow-hidden">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800/60 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
                <Eye className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                Passive Sniffer Interception (Eavesdropper)
              </h3>
            </div>
            <span className="px-2.5 py-0.5 text-[9px] font-mono font-bold uppercase tracking-widest bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-full">
              {capturedPackets.length} Sniffed
            </span>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            Demonstrates raw packet vulnerability during a blackout: The passive attacker captures unencrypted payloads transiting adjacent mesh links.
          </p>

          {capturedPackets.length === 0 ? (
            <div className="p-8 bg-slate-950/40 rounded-xl border border-slate-900 text-center">
              <p className="text-xs text-slate-500 font-mono">
                No intercepted packets yet. Transmit messages along paths adjacent to ATTACKER to trigger interception.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto border border-slate-900 rounded-xl max-h-[260px] overflow-y-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-900/80 sticky top-0 border-b border-slate-800">
                  <tr>
                    <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Packet</th>
                    <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Route</th>
                    <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Hops</th>
                    <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Intercepted Raw Payload</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 font-mono">
                  {capturedPackets.map((pkt) => (
                    <tr key={`cap-${pkt.packet_id}`} className="hover:bg-slate-850/40">
                      <td className="px-3 py-2 text-indigo-400 font-bold">{pkt.packet_id.slice(0, 8)}...</td>
                      <td className="px-3 py-2 text-slate-300">{pkt.sender_id} ➔ {pkt.receiver_id}</td>
                      <td className="px-3 py-2 text-slate-400">{pkt.hop_log?.length || 0}</td>
                      <td className="px-3 py-2">
                        <span className="px-2 py-0.5 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-bold">
                          {String(pkt.payload)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Delivery Audit Log */}
        <div className="glass-card rounded-2xl border border-slate-800/60 p-6 relative overflow-hidden">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800/60 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                <Activity className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                End-to-End Delivery Audit Log
              </h3>
            </div>
            <span className="px-2.5 py-0.5 text-[9px] font-mono font-bold uppercase tracking-widest bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 rounded-full">
              {deliveryLogs.length} Events
            </span>
          </div>

          {deliveryLogs.length === 0 ? (
            <div className="p-8 bg-slate-950/40 rounded-xl border border-slate-900 text-center">
              <p className="text-xs text-slate-500 font-mono">
                No delivery logs recorded yet. Transmit packets to generate traversal audit records.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto border border-slate-900 rounded-xl max-h-[260px] overflow-y-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-900/80 sticky top-0 border-b border-slate-800">
                  <tr>
                    <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Status</th>
                    <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Path</th>
                    <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Traversal</th>
                    <th className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 font-mono">
                  {deliveryLogs.slice(-10).reverse().map((log, i) => (
                    <tr key={`log-${log.packet_id}-${i}`} className="hover:bg-slate-850/40">
                      <td className="px-3 py-2">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border ${
                            log.status === 'delivered'
                              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                              : 'bg-red-500/10 border-red-500/20 text-red-400'
                          }`}
                        >
                          {log.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-slate-300">{log.source} ➔ {log.destination}</td>
                      <td className="px-3 py-2 text-slate-400 text-[10px]">
                        {log.route && log.route.length > 0 ? log.route.join(' ➔ ') : 'None'}
                      </td>
                      <td className="px-3 py-2 text-slate-500 text-[10px]">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
