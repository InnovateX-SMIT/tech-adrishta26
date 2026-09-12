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
