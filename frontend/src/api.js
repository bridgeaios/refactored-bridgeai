const API_BASE = '/api';

class BridgeAPI {
  constructor(baseUrl = API_BASE) {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  setToken(token) {
    this.token = token;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.detail || data.error || `HTTP ${response.status}`,
          status: response.status,
        };
      }

      return {
        success: true,
        data: data.data || data,
        status: response.status,
      };
    } catch (err) {
      return {
        success: false,
        error: err.message || 'Network error',
        status: 0,
      };
    }
  }

  // Distribution
  async runDistribution(orgId, userId, amount, idempotencyKey) {
    return this.request('/distribution/run', {
      method: 'POST',
      body: JSON.stringify({
        org_id: orgId,
        user_id: userId,
        amount: amount,
        idempotency_key: idempotencyKey,
      }),
    });
  }

  // Execution lookup
  async getExecution(executionId) {
    return this.request(`/execution/${executionId}`);
  }

  // Current user
  async getMe() {
    return this.request('/me');
  }

  // Treasury (admin only)
  async getTreasurySummary() {
    return this.request('/internal/treasury/summary');
  }
}

window.BridgeAPI = BridgeAPI;
