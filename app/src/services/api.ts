import { API_BASE_URL } from "@/constants";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    credentials: "include",
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const error: any = new Error(errorBody.detail || `HTTP Error ${response.status}: ${response.statusText}`);
    error.status = response.status;
    throw error;
  }

  return response.json();
}

export const api = {
  // Auth
  async login(username: string, password: string) {
    return request<{ access_token: string; token_type: string; user: any }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  async logout() {
    return request<{ status: string; message: string }>("/auth/logout", {
      method: "POST",
    });
  },

  async getMe() {
    return request<any>("/auth/me");
  },

  // System & Sensor Actions
  async getHealth() {
    return request<{
      status: string;
      database: string;
      sensor_mode: string;
      connections_total: number;
      alerts_total: number;
    }>("/system/health");
  },

  async fetchAndAnalyze() {
    return request<{
      status: string;
      message: string;
      new_connections_ingested: number;
      new_alerts_detected: number;
      alerts_summary: Record<string, number>;
    }>("/system/fetch-and-analyze", {
      method: "POST",
    });
  },

  async resetSensor() {
    return request<{ status: string; message: string }>("/system/reset-sensor", {
      method: "POST",
    });
  },

  async clearDatabase() {
    return request<{ status: string; message: string; deleted_connections: number; deleted_alerts: number }>(
      "/system/clear-database",
      { method: "POST" }
    );
  },

  // Alerts
  async getAlerts(params: { severity?: string; attack_type?: string; status?: string; limit?: number; offset?: number } = {}) {
    const searchParams = new URLSearchParams();
    if (params.severity) searchParams.append("severity", params.severity);
    if (params.attack_type) searchParams.append("attack_type", params.attack_type);
    if (params.status) searchParams.append("status", params.status);
    if (params.limit) searchParams.append("limit", params.limit.toString());
    if (params.offset) searchParams.append("offset", params.offset.toString());

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<{ items: any[]; total: number; limit: number; offset: number }>(`/alerts${qs}`);
  },

  async getAlertStats() {
    return request<{
      total_alerts: number;
      critical_count: number;
      high_count: number;
      medium_count: number;
      low_count: number;
      unresolved_count: number;
      top_attack_types: Array<{ attack_type: string; count: number }>;
      top_attacking_ips: Array<{ src_ip: string; count: number }>;
    }>("/alerts/stats");
  },

  async updateAlertStatus(id: number, status: string) {
    return request<any>(`/alerts/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },

  // Connections
  async getConnections(params: { limit?: number; offset?: number; proto?: string } = {}) {
    const searchParams = new URLSearchParams();
    if (params.limit) searchParams.append("limit", params.limit.toString());
    if (params.offset) searchParams.append("offset", params.offset.toString());
    if (params.proto) searchParams.append("proto", params.proto);

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<{ items: any[]; total: number; limit: number; offset: number }>(`/logs/connections${qs}`);
  },
};
