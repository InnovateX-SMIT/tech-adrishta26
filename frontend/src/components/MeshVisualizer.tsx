import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import {
  MeshNodeInfo,
  MeshTopologyResponse,
  RouteDiscoveryResponse,
  MeshPacketResponse,
  DeliveryLogSchema,
} from '../types';

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
      'NODE-A': { x: 120, y: 160 },
      'NODE-B': { x: 280, y: 160 },
      'NODE-C': { x: 440, y: 100 },
      'NODE-D': { x: 280, y: 280 },
      'NODE-E': { x: 600, y: 100 },
      'ATTACKER': { x: 440, y: 260 },
      'DEVICE-001': { x: 120, y: 160 },
      'DEVICE-002': { x: 280, y: 160 },
      'DEVICE-003': { x: 440, y: 100 },
      'DEVICE-004': { x: 280, y: 280 },
      'DEVICE-005': { x: 600, y: 100 },
    };

    if (predefined[nodeId]) {
      return predefined[nodeId];
    }

    // Dynamic circular layout fallback for custom nodes
    const angle = (index / Math.max(total, 1)) * 2 * Math.PI - Math.PI / 2;
    const centerX = 360;
    const centerY = 190;
    const radius = 150;
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
      : lastPacket?.hop_log.map((h) => h.from_node).concat(lastPacket.hop_log[lastPacket.hop_log.length - 1]?.to_node || []);

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
    <div className="mesh-visualizer-container">
      {/* Header & Quick Actions */}
      <div className="mesh-header-row">
        <div>
          <h2 className="mesh-title">
            <span className="mesh-title-icon">⚡</span> Emergency Mesh Simulation Engine
          </h2>
          <p className="mesh-subtitle">
            Decentralized peer-to-peer relay network simulation with BFS routing, node failure tolerance, and eavesdropper detection.
          </p>
        </div>
        <div className="mesh-action-buttons">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleBuildDemo(false)}
            disabled={loading}
          >
            Demo Mesh (NODE-A..E)
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleBuildDemo(true)}
            disabled={loading}
          >
            Registered Mesh (DEVICE-001..005)
          </button>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            onClick={handleReset}
            disabled={loading}
          >
            Reset Topology
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="alert alert-error" role="alert">
          <span className="alert-icon">⚠️</span>
          <span>{error}</span>
          <button type="button" className="alert-close" onClick={() => setError(null)}>×</button>
        </div>
      )}
      {successMsg && (
        <div className="alert alert-success" role="status">
          <span className="alert-icon">✓</span>
          <span>{successMsg}</span>
        </div>
      )}

      {/* Main Grid: Canvas on Left, Controls & Inspection on Right */}
      <div className="mesh-main-grid">
        {/* Left: SVG Canvas */}
        <div className="card mesh-canvas-card">
          <div className="card-header">
            <h3>Topology Canvas ({topology.nodes.length} Nodes, {topology.edges.length} Links)</h3>
            <span className="badge badge-success">P2P Mesh Simulation Active</span>
          </div>
          <div className="mesh-canvas-wrapper">
            {topology.nodes.length === 0 ? (
              <div className="mesh-empty-state">
                <p>Mesh topology is currently empty.</p>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => handleBuildDemo(false)}
                >
                  Construct 5-Node Demo Mesh
                </button>
              </div>
            ) : (
              <svg viewBox="0 0 720 380" className="mesh-svg">
                <defs>
                  {/* Neon Glow Filters */}
                  <filter id="glow-green" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                  <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                  <filter id="glow-amber" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                  <filter id="glow-pink" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="5" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                </defs>

                {/* Grid Lines Background */}
                <g className="mesh-grid-bg" opacity="0.15">
                  {Array.from({ length: 15 }).map((_, i) => (
                    <line key={`gx-${i}`} x1={i * 50} y1="0" x2={i * 50} y2="380" stroke="#4ade80" strokeWidth="0.5" />
                  ))}
                  {Array.from({ length: 8 }).map((_, i) => (
                    <line key={`gy-${i}`} x1="0" y1={i * 50} x2="720" y2={i * 50} stroke="#4ade80" strokeWidth="0.5" />
                  ))}
                </g>

                {/* Edges */}
                {topology.edges.map(([aId, bId], idx) => {
                  const nodeAIndex = topology.nodes.findIndex((n) => n.node_id === aId);
                  const nodeBIndex = topology.nodes.findIndex((n) => n.node_id === bId);
                  const posA = getNodeCoordinates(aId, nodeAIndex, topology.nodes.length);
                  const posB = getNodeCoordinates(bId, nodeBIndex, topology.nodes.length);
                  const isHighlighted = isEdgeHighlighted(aId, bId);

                  return (
                    <g key={`edge-${aId}-${bId}-${idx}`}>
                      <line
                        x1={posA.x}
                        y1={posA.y}
                        x2={posB.x}
                        y2={posB.y}
                        stroke={isHighlighted ? '#38bdf8' : '#334155'}
                        strokeWidth={isHighlighted ? 3.5 : 1.5}
                        strokeDasharray={isHighlighted ? '6 3' : undefined}
                        filter={isHighlighted ? 'url(#glow-cyan)' : undefined}
                        className={isHighlighted ? 'mesh-edge-animated' : ''}
                      />
                    </g>
                  );
                })}

                {/* Nodes */}
                {topology.nodes.map((node, idx) => {
                  const pos = getNodeCoordinates(node.node_id, idx, topology.nodes.length);
                  const isSource = node.node_id === sourceNode;
                  const isDest = node.node_id === destNode;
                  const isSelected = node.node_id === selectedNodeId;
                  const isRouteNode = discoveredRoute?.path.includes(node.node_id);
                  const isCurrentHop = simulatingHop >= 0 && lastPacket?.hop_log?.[simulatingHop]?.to_node === node.node_id;

                  let fillColor = node.is_online ? '#0f172a' : '#270810';
                  let strokeColor = node.is_online ? '#10b981' : '#ef4444';
                  let filter = node.is_online ? 'url(#glow-green)' : undefined;

                  if (node.is_attacker) {
                    strokeColor = '#f59e0b';
                    fillColor = '#1c1303';
                    filter = 'url(#glow-amber)';
                  }
                  if (isCurrentHop) {
                    strokeColor = '#ec4899';
                    fillColor = '#3b0720';
                    filter = 'url(#glow-pink)';
                  } else if (isSource) {
                    strokeColor = '#38bdf8';
                    filter = 'url(#glow-cyan)';
                  } else if (isDest) {
                    strokeColor = '#a855f7';
                    filter = 'url(#glow-amber)';
                  }

                  return (
                    <g
                      key={`node-${node.node_id}`}
                      className="mesh-node-group"
                      onClick={() => inspectNode(node.node_id)}
                      style={{ cursor: 'pointer' }}
                    >
                      {/* Selection / Active Hop Ring */}
                      {(isSelected || isSource || isDest || isCurrentHop) && (
                        <circle
                          cx={pos.x}
                          cy={pos.y}
                          r={isCurrentHop ? 32 : 28}
                          fill="none"
                          stroke={isCurrentHop ? '#ec4899' : isSource ? '#38bdf8' : isDest ? '#a855f7' : '#94a3b8'}
                          strokeWidth={isCurrentHop ? 2.5 : 1.5}
                          strokeDasharray={isCurrentHop ? '2 2' : '4 2'}
                        />
                      )}

                      {/* Main Node Body */}
                      <circle
                        cx={pos.x}
                        cy={pos.y}
                        r={22}
                        fill={fillColor}
                        stroke={strokeColor}
                        strokeWidth={node.is_attacker ? 2.5 : 2}
                        filter={filter}
                      />

                      {/* Status indicator pill inside node */}
                      <circle
                        cx={pos.x + 14}
                        cy={pos.y - 14}
                        r={5}
                        fill={node.is_online ? '#10b981' : '#ef4444'}
                      />

                      {/* Node Label */}
                      <text
                        x={pos.x}
                        y={pos.y + 4}
                        fill="#f8fafc"
                        fontSize="10"
                        fontWeight="600"
                        textAnchor="middle"
                        fontFamily="monospace"
                      >
                        {node.is_attacker ? 'SNIFFER' : node.node_id}
                      </text>

                      {/* Sub-label */}
                      <text
                        x={pos.x}
                        y={pos.y + 36}
                        fill={node.is_online ? '#94a3b8' : '#ef4444'}
                        fontSize="9"
                        textAnchor="middle"
                      >
                        {node.is_attacker
                          ? '⚠️ Eavesdropper'
                          : node.is_online
                          ? (isSource ? '● SOURCE' : isDest ? '● DEST' : isRouteNode ? '⚡ RELAY' : 'ONLINE')
                          : '✕ OFFLINE'}
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
          <div className="mesh-legend">
            <span className="legend-item"><span className="legend-dot dot-online"></span> Online Relay</span>
            <span className="legend-item"><span className="legend-dot dot-offline"></span> Offline (Bridge Out)</span>
            <span className="legend-item"><span className="legend-dot dot-attacker"></span> Passive Attacker (Sniffer)</span>
            <span className="legend-item"><span className="legend-line line-route"></span> Discovered Route</span>
          </div>
        </div>

        {/* Right: Controls & Discovery Panel */}
        <div className="mesh-controls-col">
          {/* Path Discovery & Simulation Card */}
          <div className="card">
            <div className="card-header">
              <h3>Route & Packet Dispatch</h3>
            </div>
            <div className="mesh-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="mesh-source">Source Node</label>
                  <select
                    id="mesh-source"
                    className="form-control"
                    value={sourceNode}
                    onChange={(e) => setSourceNode(e.target.value)}
                  >
                    {topology.nodes.map((n) => (
                      <option key={`src-${n.node_id}`} value={n.node_id}>
                        {n.node_id} {!n.is_online ? '(OFFLINE)' : n.is_attacker ? '(ATTACKER)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="mesh-dest">Destination Node</label>
                  <select
                    id="mesh-dest"
                    className="form-control"
                    value={destNode}
                    onChange={(e) => setDestNode(e.target.value)}
                  >
                    {topology.nodes.map((n) => (
                      <option key={`dst-${n.node_id}`} value={n.node_id}>
                        {n.node_id} {!n.is_online ? '(OFFLINE)' : n.is_attacker ? '(ATTACKER)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="mesh-ttl">TTL (Max Hops)</label>
                  <input
                    id="mesh-ttl"
                    type="number"
                    min="1"
                    max="50"
                    className="form-control"
                    value={ttl}
                    onChange={(e) => setTtl(parseInt(e.target.value, 10) || 10)}
                  />
                </div>
                <div className="form-group flex-2">
                  <label htmlFor="mesh-payload">Simulation Payload</label>
                  <input
                    id="mesh-payload"
                    type="text"
                    className="form-control"
                    value={payloadText}
                    onChange={(e) => setPayloadText(e.target.value)}
                    placeholder="Enter test message payload..."
                  />
                </div>
              </div>

              <div className="mesh-btn-group">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleDiscoverRoute}
                  disabled={loading || !sourceNode || !destNode}
                >
                  🔍 Discover Route (BFS)
                </button>
                <button
                  type="button"
                  className="btn btn-success"
                  onClick={handleSimulateTransmission}
                  disabled={loading || !sourceNode || !destNode}
                >
                  🚀 Simulate Transmission
                </button>
              </div>

              {/* Route Summary Box */}
              {discoveredRoute && (
                <div className={`mesh-route-box ${discoveredRoute.reachable ? 'route-success' : 'route-failed'}`}>
                  <div className="route-box-header">
                    <strong>
                      {discoveredRoute.reachable ? '✓ Route Discovered' : '✕ No Route Available'}
                    </strong>
                    {discoveredRoute.reachable && (
                      <span className="badge badge-info">{discoveredRoute.hop_count} Hops</span>
                    )}
                  </div>
                  {discoveredRoute.reachable ? (
                    <div className="route-path-flow">
                      {discoveredRoute.path.map((node, i) => (
                        <React.Fragment key={`hop-${node}`}>
                          <span className="route-hop-badge">{node}</span>
                          {i < discoveredRoute.path.length - 1 && <span className="route-arrow">➔</span>}
                        </React.Fragment>
                      ))}
                    </div>
                  ) : (
                    <p className="route-error-desc">
                      {discoveredRoute.failure_reason || 'Path could not be determined due to disconnected or offline nodes.'}
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Node Inspector Card */}
          <div className="card">
            <div className="card-header">
              <h3>Node Controller & Inspector</h3>
            </div>
            {selectedNodeId ? (
              (() => {
                const node = topology.nodes.find((n) => n.node_id === selectedNodeId);
                if (!node) return <p className="text-muted">Node not found in topology.</p>;
                return (
                  <div className="node-inspector-content">
                    <div className="inspector-header">
                      <div>
                        <h4>{node.node_id}</h4>
                        <span className={node.is_online ? 'badge badge-success' : 'badge badge-danger'}>
                          {node.is_online ? 'ONLINE' : 'OFFLINE'}
                        </span>
                        {node.is_attacker && <span className="badge badge-warning">ATTACKER</span>}
                      </div>
                      <button
                        type="button"
                        className={node.is_online ? 'btn btn-danger btn-sm' : 'btn btn-success btn-sm'}
                        onClick={() => handleToggleOnline(node)}
                      >
                        {node.is_online ? 'Simulate Outage (Go Offline)' : 'Restore Node (Go Online)'}
                      </button>
                    </div>

                    <div className="inspector-details">
                      <p><strong>Direct Neighbors:</strong> {node.neighbors.length > 0 ? node.neighbors.join(', ') : 'None (Isolated)'}</p>
                      <p><strong>Relay Capable:</strong> {node.is_available_for_relay ? 'Yes' : 'No'}</p>
                      <p><strong>Delivered Inbox:</strong> {nodeInbox.length} packet(s)</p>
                    </div>
                  </div>
                );
              })()
            ) : (
              <p className="text-muted text-center" style={{ padding: '20px' }}>
                Click any node on the canvas to inspect its status or toggle its online/offline availability.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Grid: Attacker Sniffing Observation vs Delivery Audit Log */}
      <div className="mesh-bottom-grid">
        {/* Attacker Sniffing Panel */}
        <div className="card attacker-card">
          <div className="card-header">
            <h3>📡 Attacker Sniffing Panel (Passive Interception)</h3>
            <span className="badge badge-warning">{capturedPackets.length} Intercepted</span>
          </div>
          <div className="card-body">
            <p className="panel-desc">
              Demonstrates packet sniffing vulnerability: The attacker node captures traffic transiting any adjacent edge, even though it is neither sender nor receiver.
            </p>
            {capturedPackets.length === 0 ? (
              <p className="text-muted text-center" style={{ padding: '16px' }}>
                No packets intercepted yet. Transmit a packet through edges adjacent to ATTACKER to observe passive sniffing.
              </p>
            ) : (
              <div className="table-responsive">
                <table className="table table-dark table-sm">
                  <thead>
                    <tr>
                      <th>Packet ID</th>
                      <th>Sender</th>
                      <th>Receiver</th>
                      <th>Traversed Hops</th>
                      <th>Intercepted Payload</th>
                    </tr>
                  </thead>
                  <tbody>
                    {capturedPackets.map((pkt) => (
                      <tr key={`cap-${pkt.packet_id}`}>
                        <td><code>{pkt.packet_id.slice(0, 8)}...</code></td>
                        <td>{pkt.sender_id}</td>
                        <td>{pkt.receiver_id}</td>
                        <td>{pkt.hop_log?.length || 0}</td>
                        <td><span className="badge badge-danger">{String(pkt.payload)}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Delivery Audit Log Panel */}
        <div className="card">
          <div className="card-header">
            <h3>Audit Log (End-to-End Traversal Trail)</h3>
            <span className="badge badge-info">{deliveryLogs.length} Events</span>
          </div>
          <div className="card-body">
            {deliveryLogs.length === 0 ? (
              <p className="text-muted text-center" style={{ padding: '16px' }}>
                No delivery logs recorded yet.
              </p>
            ) : (
              <div className="table-responsive" style={{ maxHeight: '240px', overflowY: 'auto' }}>
                <table className="table table-dark table-sm">
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Source ➔ Dest</th>
                      <th>Hops</th>
                      <th>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deliveryLogs.slice(-8).reverse().map((log, i) => (
                      <tr key={`log-${log.packet_id}-${i}`}>
                        <td>
                          <span className={log.status === 'delivered' ? 'badge badge-success' : 'badge badge-danger'}>
                            {log.status.toUpperCase()}
                          </span>
                        </td>
                        <td>{log.source} ➔ {log.destination}</td>
                        <td>{log.route && log.route.length > 0 ? log.route.join(' ➔ ') : 'None'}</td>
                        <td className="text-muted">{new Date(log.timestamp).toLocaleTimeString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
