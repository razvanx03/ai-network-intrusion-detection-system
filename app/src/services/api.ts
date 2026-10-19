import { API_BASE_URL } from "@/constants";
import type {
  Alert,
  AlertStats,
  AlertStatus,
  AnalysisResult,
  ClearResult,
  Connection,
  Health,
  Operation,
  Page,
  Severity,
  User,
} from "./types";
export class ApiError extends Error {
  readonly status: number;
  constructor(status: number) {
    super(`API request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
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
    throw new ApiError(response.status);
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
  fetchAndAnalyze: () =>
    request<AnalysisResult>("/system/fetch-and-analyze", { method: "POST" }),
  resetSensor: () =>
    request<Operation>("/system/reset-sensor", { method: "POST" }),
  clearDatabase: () =>
    request<ClearResult>("/system/clear-database", { method: "POST" }),
  getAlerts: (
    params: { severity?: Severity; limit?: number; offset?: number } = {},
    signal?: AbortSignal,
  ) => request<Page<Alert>>(`/alerts${query(params)}`, { signal }),
  getAlertStats: (signal?: AbortSignal) =>
    request<AlertStats>("/alerts/stats", { signal }),
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
  async downloadAlertsExport(format: "csv" | "json", severity?: Severity) {
    const response = await responseFor(
      `/alerts/export${query({ format, severity })}`,
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
