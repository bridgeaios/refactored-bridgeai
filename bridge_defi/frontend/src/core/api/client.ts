import { err, ok, type ApiResponse } from './types';

const BASE =
  (import.meta as ImportMeta & { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
    });

    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as {
        code?: string;
        message?: string;
      };
      return err(body.code ?? `HTTP_${response.status}`, body.message ?? response.statusText);
    }

    return ok((await response.json()) as T);
  } catch (error) {
    return err('NETWORK_ERROR', error instanceof Error ? error.message : 'Network error');
  }
}

async function get<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  return request<T>(path, { ...(init ?? {}), method: init?.method ?? 'GET' });
}

async function post<T>(path: string, body: unknown, init?: RequestInit): Promise<ApiResponse<T>> {
  return request<T>(path, {
    ...(init ?? {}),
    method: 'POST',
    body: JSON.stringify(body),
  });
}

async function put<T>(path: string, body: unknown, init?: RequestInit): Promise<ApiResponse<T>> {
  return request<T>(path, {
    ...(init ?? {}),
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

export const economy = {
  getTreasuryStatus: () => get<unknown>('/api/treasury/status'),
  getTreasurySummary: () => get<unknown>('/api/treasury/summary'),
  getTreasuryLedger: () => get<unknown>('/api/treasury/ledger'),
  collectRevenue: (payload: unknown) => post<unknown>('/api/treasury/collect', payload),
  disburse: (payload: unknown) => post<unknown>('/api/treasury/disburse', payload),
  getMarketplaceOpen: () => get<unknown>('/api/marketplace/open'),
  completeTask: (payload: unknown) => post<unknown>('/api/marketplace/complete', payload),
  pledgeTask: (payload: unknown) => post<unknown>('/api/marketplace/pledge', payload),
  distributeUbi: (payload: unknown) => post<unknown>('/api/ubi/distribute', payload),
  getEconWeights: () => get<unknown>('/api/econ/weights'),
  getCircuitBreaker: () => get<unknown>('/api/econ/circuit-breaker'),
};

export const twins = {
  getAll: () => get<unknown>('/api/twins'),
  decide: (payload: unknown) => post<unknown>('/api/twin/decide', payload),
  getProfile: () => get<unknown>('/api/twin/profile'),
  getSharedXml: () => get<unknown>('/api/twin/shared-xml'),
  teach: (payload: unknown) => post<unknown>('/api/twins/teach', payload),
  getLeaderboard: () => get<unknown>('/api/twins/leaderboard'),
};

export const governance = {
  getKnowledgeGraph: () => get<unknown>('/api/knowledge-graph'),
  getReputation: () => get<unknown>('/api/reputation/top'),
  getMissions: () => get<unknown>('/api/missions'),
  auditDrift: () => get<unknown>('/api/audit/drift'),
};

export const network = {
  getSwarmHealth: () => get<unknown>('/api/swarm/health'),
  getLiveReport: () => get<unknown>('/api/live/report'),
  getLiveMap: () => get<unknown>('/api/live/map'),
  getProjects: () => get<unknown>('/api/projects'),
  registerProject: (payload: unknown) => post<unknown>('/api/projects/register', payload),
};

export const infra = {
  getUserSettings: () => get<unknown>('/api/user/settings'),
  putUserSettings: (payload: unknown) => put<unknown>('/api/user/settings', payload),
  getStatus: () => get<unknown>('/api/status'),
  getTelemetry: () => get<unknown>('/api/telemetry'),
  getCapabilities: () => get<unknown>('/api/capabilities'),
  siweLogin: (payload: unknown) => post<unknown>('/api/auth/siwe', payload),
};

export const api = {
  economy,
  twins,
  governance,
  network,
  infra,
};
