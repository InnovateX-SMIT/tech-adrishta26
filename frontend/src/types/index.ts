export interface HealthResponse {
  status: string;
  service: string;
  phase: string;
}

export interface SystemInfoResponse {
  project: string;
  mode: string;
  mesh_enabled: boolean;
  encryption_enabled: boolean;
  phase: number;
}

export type ConnectionState = 'idle' | 'loading' | 'connected' | 'error';

export interface ApiError {
  message: string;
  timestamp: string;
}

export type MemberStatus = 'active' | 'revoked';

export interface RescueMember {
  rescue_id: string;
  name: string;
  team: string;
  role: string;
  device_id: string;
  signing_public_key: string | null;
  encryption_public_key: string | null;
  status: MemberStatus;
  created_at: string;
  revoked_at: string | null;
}

export interface RegisterMemberRequest {
  name: string;
  team: string;
  role: string;
}

export interface MemberStatusResponse {
  rescue_id: string;
  status: MemberStatus;
  is_active: boolean;
}

export interface DeviceCryptoInitResponse {
  device_id: string;
  rescue_id: string;
  signing_public_key: string;
  encryption_public_key: string;
  status: string;
  algorithms: Record<string, string>;
}

export interface DeviceCryptoStatusResponse {
  device_id: string;
  rescue_id: string;
  is_initialized: boolean;
  signing_public_key: string | null;
  encryption_public_key: string | null;
  algorithms: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Phase 4 — Mesh Simulation Types
// ---------------------------------------------------------------------------

export interface MeshNodeInfo {
  node_id: string;
  neighbors: string[];
  is_attacker: boolean;
  is_online: boolean;
  is_available_for_relay: boolean;
}

export interface MeshTopologyResponse {
  nodes: MeshNodeInfo[];
  edges: [string, string][];
}

export interface RouteDiscoveryResponse {
  source_device_id: string;
  destination_device_id: string;
  reachable: boolean;
  path: string[];
  hop_count: number;
  failure_reason: string | null;
}

export interface HopRecordSchema {
  hop_number: number;
  from_node: string;
  to_node: string;
  timestamp: string;
}

export interface MeshPacketResponse {
  packet_id: string;
  sender_id: string;
  receiver_id: string;
  payload: any;
  status: string;
  ttl: number;
  hop_log: HopRecordSchema[];
}

export interface CapturedPacketsResponse {
  node_id: string;
  captured: MeshPacketResponse[];
}

export interface DeliveryLogSchema {
  packet_id: string;
  source: string;
  destination: string;
  route: string[];
  hops: HopRecordSchema[];
  status: string;
  error: string | null;
  timestamp: string;
}
