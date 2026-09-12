import { HealthResponse, SystemInfoResponse } from '../types';

const API_BASE_URL: string = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '');

const DEFAULT_TIMEOUT_MS = 5000;

async function requestWithTimeout<T>(path: string, timeoutMs: number = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = `${API_BASE_URL}${path}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`API error ${response.status}: ${response.statusText}`);
    }

    const data: T = await response.json();
    return data;
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error(`Connection to backend timed out after ${timeoutMs}ms. Verify backend is running at ${API_BASE_URL}`);
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
};
