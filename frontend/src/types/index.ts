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

// ---------------------------------------------------------------------------
// Phase 5 & 6 — Secure Messaging & Authorization Gate Types
// ---------------------------------------------------------------------------

export interface SecureMessagePayload {
  version: number;
  packet_id: string;
  message_id: string;
  sender_rescue_id: string;
  sender_device_id: string;
  recipient_rescue_id: string;
  recipient_device_id: string;
  timestamp: number;
  key_agreement: string;
  kdf: string;
  cipher: string;
  ephemeral_public_key: string;
  salt: string;
  nonce: string;
  ciphertext: string;
  signature: string;
}

export interface SendMessageRequest {
  sender_id: string;
  recipient_id: string;
  message: string;
  priority?: string;
}

export interface SendMessageResponse {
  packet_id: string;
  message_id: string;
  sender_id: string;
  recipient_id: string;
  status: string;
  hop_log: HopRecordSchema[];
  payload: SecureMessagePayload;
}

export interface InboxMessageSummary {
  packet_id: string;
  message_id: string;
  sender_rescue_id: string;
  sender_device_id: string;
  recipient_rescue_id: string;
  recipient_device_id: string;
  timestamp: number;
  status: string;
  payload: SecureMessagePayload;
}

export interface DecryptMessageRequest {
  recipient_id: string;
  packet_id?: string;
  payload?: SecureMessagePayload;
}

export interface DecryptMessageResponse {
  status: 'SUCCESS' | 'REJECTED';
  message?: string | null;
  sender_name?: string | null;
  sender_id?: string | null;
  packet_id?: string | null;
  message_id?: string | null;
  reason?: string | null;
  detail?: string | null;
}


export type MessageStatus =
  | 'CREATED'
  | 'ENCRYPTED'
  | 'ROUTING'
  | 'IN_TRANSIT'
  | 'DELIVERED'
  | 'DECRYPTED'
  | 'FAILED'
  | 'EXPIRED'
  | 'QUEUED';

export interface MessageRecord {
  message_id: string;
  packet_id: string;
  sender_device_id: string;
  recipient_device_id: string;
  sender_rescue_id: string;
  recipient_rescue_id: string;
  conversation_id: string;
  created_at: number;
  delivered_at?: number | null;
  decrypted_at?: number | null;
  status: MessageStatus;
  failure_reason?: string | null;
  retry_count: number;
  hop_count: number;
  route: string[];
  payload: SecureMessagePayload;
}

export interface MessageStatusResponse {
  message_id: string;
  packet_id: string;
  sender_id: string;
  recipient_id: string;
  status: MessageStatus;
  created_at: number;
  delivered_at?: number | null;
  decrypted_at?: number | null;
  retry_count: number;
  hop_count: number;
  route: string[];
  failure_reason?: string | null;
}

export interface ConversationResponse {
  conversation_id: string;
  device_a: string;
  device_b: string;
  total_messages: number;
  messages: MessageRecord[];
}

// Phase 7: Attack Simulation & Contrast Mode
export type SimulationMode = 'vulnerable' | 'protected';

export interface CapturedPacket {
  simulation_id: string;
  capture_id: string;
  packet_id: string;
  message_id: string;
  captured_at: string;
  captured_at_node: string;
  sender_id: string;
  recipient_id: string;
  route: string[];
  communication_mode: SimulationMode;
  packet_size: number;
  metadata_visible_to_attacker: boolean;
  contains_plaintext: boolean;
  plaintext_exposed: boolean;
  ciphertext_present: boolean;
  signature_present: boolean;
  sniffed_content: string;
  message_readable_by_attacker: boolean;
  security_result: string;
  explanation: string;
  raw_payload?: Record<string, unknown> | null;
}

export interface SimulateAttackRequest {
  mode: SimulationMode;
  sender_id: string;
  recipient_id: string;
  message: string;
  attacker_node_id?: string | null;
}

export interface SimulateAttackResponse {
  simulation_id: string;
  mode: SimulationMode;
  packet_id: string;
  message_id: string;
  captured: boolean;
  captured_packet: CapturedPacket | null;
  route: string[];
  receiver_result: Record<string, unknown>;
  security_logs: string[];
  summary_sentence: string;
}

export interface TamperCaptureRequest {
  capture_id: string;
  tamper_field: 'ciphertext' | 'signature' | 'nonce';
  recipient_id?: string | null;
}

export interface TamperCaptureResponse {
  capture_id: string;
  tampered_field: string;
  receiver_status: string;
  rejection_reason?: string | null;
  rejection_detail?: string | null;
  plaintext_revealed: boolean;
  explanation: string;
}

export interface AttackStatusResponse {
  total_captures: number;
  vulnerable_captures: number;
  protected_captures: number;
  last_capture?: CapturedPacket | null;
}



