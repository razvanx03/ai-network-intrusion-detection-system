import { API_BASE_URL } from "@/constants";
import type {
  Alert,
  AlertStats,
  AlertStatus,
  AnalysisResult,
  AnalysisSession,
  AnalysisConnection,
  ClearResult,
  Connection,
  Health,
  Operation,
  Page,
  Severity,
  User,
  Overview,
  SensorStatus,
  Provenance,
} from "./types";
export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  constructor(status: number, code?: string) {
    super(`API request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}
const sessionListeners = new Set<() => void>();
export function onSessionInvalid(listener: () => void) {
  sessionListeners.add(listener);
  return () => {
    sessionListeners.delete(listener);
  };
}
async function responseFor(
  endpoint: string,
  options: RequestInit = {},
): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      credentials: "include",
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(0);
  }
  if (!response.ok) {
    if (
      (response.status === 401 || response.status === 403) &&
      endpoint !== "/auth/login"
    )
      sessionListeners.forEach((listener) => listener());
    let code: string | undefined;
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body && body.detail && typeof body.detail === "object" && "code" in body.detail && typeof body.detail.code === "string") code = body.detail.code;
    } catch {
      // An HTTP error may have no JSON body; its status remains authoritative.
    }
    throw new ApiError(response.status, code);
  }
  return response;
}
async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await responseFor(endpoint, options);
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(502);
  }
}
function query(params: Record<string, string | number | undefined>) {
  const result = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") result.set(key, String(value));
  });
  return `?${result}`;
}
export const api = {
  login: (username: string, password: string) =>
    request<{ user: User; expires_in_minutes: number }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<Operation>("/auth/logout", { method: "POST" }),
  getMe: (signal?: AbortSignal) => request<User>("/auth/me", { signal }),
  getHealth: (signal?: AbortSignal) =>
    request<Health>("/system/health", { signal }),
  getOverview: (signal?: AbortSignal) => request<Overview>("/system/overview", { signal }),
  getSensorStatus: (signal?: AbortSignal) => request<SensorStatus>("/system/sensor-status", { signal }),
  analyzeStored: (connection_ids: number[]) => request<AnalysisResult>("/analysis-sessions", {
    method: "POST", body: JSON.stringify({ source: "stored", connection_ids }),
  }),
  fetchAndAnalyze: () =>
    request<AnalysisResult>("/system/fetch-and-analyze", { method: "POST" }),
  getAnalysisSessions: (offset: number, signal?: AbortSignal) =>
    request<Page<AnalysisSession>>(`/analysis-sessions${query({ limit: 5, offset })}`, { signal }),
  getAnalysisSession: (id: string, signal?: AbortSignal) =>
    request<AnalysisSession>(`/analysis-sessions/${encodeURIComponent(id)}`, { signal }),
  getAnalysisConnections: (id: string, offset: number, signal?: AbortSignal) =>
    request<Page<AnalysisConnection>>(`/analysis-sessions/${encodeURIComponent(id)}/connections${query({ limit: 10, offset })}`, { signal }),
  getAnalysisAlerts: (id: string, offset: number, signal?: AbortSignal) =>
    request<Page<Alert>>(`/analysis-sessions/${encodeURIComponent(id)}/alerts${query({ limit: 5, offset })}`, { signal }),
  resetSensor: () =>
    request<Operation>("/system/reset-sensor", { method: "POST" }),
  getAlertConnections: (session: string, id: number, offset: number, signal?: AbortSignal) =>
    request<Page<Connection>>(`/analysis-sessions/${encodeURIComponent(session)}/alerts/${id}/connections${query({ limit: 10, offset })}`, { signal }),
  clearDatabase: () =>
    request<ClearResult>("/system/clear-database", { method: "POST" }),
  getAlerts: (
    params: { severity?: Severity; status?: AlertStatus; provenance?: Provenance; limit?: number; offset?: number } = {},
    signal?: AbortSignal,
  ) => request<Page<Alert>>(`/alerts${query(params)}`, { signal }),
  getAlertStats: (signal?: AbortSignal) =>
    request<AlertStats>("/alerts/stats?provenance=analysis", { signal }),
  updateAlertStatus: (id: number, status: AlertStatus) =>
    request<Alert>(`/alerts/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  getConnections: (
    params: { proto?: string; limit?: number; offset?: number } = {},
    signal?: AbortSignal,
  ) =>
    request<Page<Connection>>(`/logs/connections${query(params)}`, { signal }),
  async downloadAlertsExport(format: "csv" | "json", severity?: Severity, provenance: Provenance = "analysis") {
    const response = await responseFor(
      `/alerts/export${query({ format, severity, provenance })}`,
    );
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `nids_alerts_${new Date().toISOString().slice(0, 10)}.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
