import {
  HealthResponse,
  SystemInfoResponse,
  RescueMember,
  RegisterMemberRequest,
  MemberStatusResponse,
} from '../types';

const API_BASE_URL: string = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '');

const DEFAULT_TIMEOUT_MS = 6000;

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  timeoutMs?: number;
}

async function requestWithTimeout<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = `${API_BASE_URL}${path}`;
    const headers: Record<string, string> = {
      'Accept': 'application/json',
    };

    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    if (!response.ok) {
      let errorDetail = `API error ${response.status}: ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          if (Array.isArray(errorJson.detail)) {
            errorDetail = errorJson.detail.map((d: { msg: string }) => d.msg).join('; ');
          } else {
            errorDetail = String(errorJson.detail);
          }
        }
      } catch {
        // Fallback to response.statusText
      }
      throw new Error(errorDetail);
    }

    const data: T = await response.json();
    return data;
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error(`Connection timed out after ${timeoutMs}ms. Verify backend is running at ${API_BASE_URL}`);
    }
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new Error(`Cannot reach backend server at ${API_BASE_URL}. Ensure uvicorn is running.`);
    }
    if (err instanceof Error) {
      throw err;
    }
    throw new Error('An unknown network error occurred.');
  } finally {
    clearTimeout(timer);
  }
}

export const apiService = {
  getBaseUrl(): string {
    return API_BASE_URL;
  },

  async getHealth(): Promise<HealthResponse> {
    return requestWithTimeout<HealthResponse>('/api/health');
  },

  async getSystemInfo(): Promise<SystemInfoResponse> {
    return requestWithTimeout<SystemInfoResponse>('/api/system/info');
  },

  async fetchMembers(): Promise<RescueMember[]> {
    return requestWithTimeout<RescueMember[]>('/api/registry/members');
  },

  async registerMember(payload: RegisterMemberRequest): Promise<RescueMember> {
    return requestWithTimeout<RescueMember>('/api/registry/members', {
      method: 'POST',
      body: payload,
    });
  },

  async fetchMemberByRescueId(rescueId: string): Promise<RescueMember> {
    return requestWithTimeout<RescueMember>(`/api/registry/members/${encodeURIComponent(rescueId)}`);
  },

  async fetchMemberByDeviceId(deviceId: string): Promise<RescueMember> {
    return requestWithTimeout<RescueMember>(`/api/registry/devices/${encodeURIComponent(deviceId)}`);
  },

  async fetchMemberStatus(rescueId: string): Promise<MemberStatusResponse> {
    return requestWithTimeout<MemberStatusResponse>(`/api/registry/members/${encodeURIComponent(rescueId)}/status`);
  },

  async revokeMember(rescueId: string): Promise<MemberStatusResponse> {
    return requestWithTimeout<MemberStatusResponse>(`/api/registry/members/${encodeURIComponent(rescueId)}/revoke`, {
      method: 'POST',
    });
  },

  async initializeDeviceKeys(deviceId: string): Promise<import('../types').DeviceCryptoInitResponse> {
    return requestWithTimeout<import('../types').DeviceCryptoInitResponse>(`/api/crypto/devices/${encodeURIComponent(deviceId)}/initialize`, {
      method: 'POST',
    });
  },

  async fetchDeviceCryptoStatus(deviceId: string): Promise<import('../types').DeviceCryptoStatusResponse> {
    return requestWithTimeout<import('../types').DeviceCryptoStatusResponse>(`/api/crypto/devices/${encodeURIComponent(deviceId)}/status`);
  },

  // -------------------------------------------------------------------------
  // Phase 4 — Mesh Network Simulation
  // -------------------------------------------------------------------------

  async fetchMeshTopology(): Promise<import('../types').MeshTopologyResponse> {
    return requestWithTimeout<import('../types').MeshTopologyResponse>('/api/mesh/topology');
  },

  async buildMeshDemo(useDeviceIds: boolean = false): Promise<{ message: string; node_count: number; edge_count: number }> {
    return requestWithTimeout<{ message: string; node_count: number; edge_count: number }>(`/api/mesh/demo?use_device_ids=${useDeviceIds}`, {
      method: 'POST',
    });
  },

  async findMeshRoute(sourceId: string, destId: string): Promise<import('../types').RouteDiscoveryResponse> {
    return requestWithTimeout<import('../types').RouteDiscoveryResponse>(
      `/api/mesh/routes/${encodeURIComponent(sourceId)}/${encodeURIComponent(destId)}`
    );
  },

  async sendMeshPacket(senderId: string, receiverId: string, payload: any, ttl: number = 10): Promise<import('../types').MeshPacketResponse> {
    return requestWithTimeout<import('../types').MeshPacketResponse>('/api/mesh/send', {
      method: 'POST',
      body: {
        sender_id: senderId,
        receiver_id: receiverId,
        payload,
        ttl,
      },
    });
  },

  async updateNodeState(nodeId: string, updates: { is_online?: boolean; is_available_for_relay?: boolean }): Promise<import('../types').MeshNodeInfo> {
    return requestWithTimeout<import('../types').MeshNodeInfo>(`/api/mesh/nodes/${encodeURIComponent(nodeId)}`, {
      method: 'PATCH',
      body: updates,
    });
  },

  async fetchNodeInbox(nodeId: string): Promise<import('../types').MeshPacketResponse[]> {
    return requestWithTimeout<import('../types').MeshPacketResponse[]>(`/api/mesh/node/${encodeURIComponent(nodeId)}/inbox`);
  },

  async fetchAttackerCaptured(nodeId: string): Promise<import('../types').CapturedPacketsResponse> {
    return requestWithTimeout<import('../types').CapturedPacketsResponse>(`/api/mesh/node/${encodeURIComponent(nodeId)}/captured`);
  },

  async resetMeshNetwork(): Promise<{ message: string }> {
    return requestWithTimeout<{ message: string }>('/api/mesh/reset', {
      method: 'DELETE',
    });
  },

  async fetchMeshLogs(): Promise<import('../types').DeliveryLogSchema[]> {
    return requestWithTimeout<import('../types').DeliveryLogSchema[]>('/api/mesh/logs');
  },

  async connectMeshNodes(nodeA: string, nodeB: string): Promise<any> {
    return requestWithTimeout<any>('/api/mesh/connect', {
      method: 'POST',
      body: { node_a: nodeA, node_b: nodeB },
    });
  },

  async disconnectMeshNodes(nodeA: string, nodeB: string): Promise<any> {
    return requestWithTimeout<any>('/api/mesh/disconnect', {
      method: 'POST',
      body: { node_a: nodeA, node_b: nodeB },
    });
  },

  // -------------------------------------------------------------------------
  // Phase 5 & 6 — Secure Messaging & Authorization Gate
  // -------------------------------------------------------------------------

  async sendSecureMessage(
    payload: import('../types').SendMessageRequest
  ): Promise<import('../types').SendMessageResponse> {
    return requestWithTimeout<import('../types').SendMessageResponse>('/api/messages/send', {
      method: 'POST',
      body: payload,
    });
  },

  async fetchDeviceInbox(
    recipientId: string
  ): Promise<import('../types').InboxMessageSummary[]> {
    return requestWithTimeout<import('../types').InboxMessageSummary[]>(
      `/api/messages/inbox/${encodeURIComponent(recipientId)}`
    );
  },

  async decryptMessage(
    payload: import('../types').DecryptMessageRequest
  ): Promise<import('../types').DecryptMessageResponse> {
    return requestWithTimeout<import('../types').DecryptMessageResponse>('/api/messages/decrypt', {
      method: 'POST',
      body: payload,
    });
  },
};

