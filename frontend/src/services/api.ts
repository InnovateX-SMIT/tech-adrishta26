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
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
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
};
