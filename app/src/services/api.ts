import { API_BASE_URL } from "@/constants";
import type {
  Alert,
  AlertStats,
  DailyAlerts,
  AlertStatus,
  AnalysisResult,
  AnalysisSession,
  AnalysisConnection,
  ArchiveBatch,
  Connection,
  Operation,
  Page,
  User,
  Overview,
  ContextType,
  ProtocolEvent,
  SensorStatus,
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
function query(params: Record<string, string | number | boolean | undefined>) {
  const result = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") result.set(key, String(value));
  });
  return `?${result}`;
}
export const api = {
  getSensorStatus: (signal?: AbortSignal) => request<SensorStatus>("/system/sensor-status", { signal }),
  getConnectionEvents: (id: number, kind: ContextType, offset: number, signal?: AbortSignal, includeArchived = false) =>
    request<Page<ProtocolEvent>>(`/logs/connections/${id}/events${query({ kind, limit: 50, offset, include_archived: includeArchived })}`, { signal }),
  login: (username: string, password: string) =>
    request<{ user: User; expires_in_minutes: number }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<Operation>("/auth/logout", { method: "POST" }),
  getMe: (signal?: AbortSignal) => request<User>("/auth/me", { signal }),
  getOverview: (signal?: AbortSignal) => request<Overview>("/system/overview", { signal }),
  fetchAndAnalyze: () => request<AnalysisResult>("/system/fetch-and-analyze", { method: "POST" }),
  getAnalysisSessions: async (signal?: AbortSignal, includeArchived = false, archivedOnly = false) => {
    const items: AnalysisSession[] = [];
    let total: number;
    do {
      const page = await request<Page<AnalysisSession>>(`/analysis-sessions${query({ limit: 100, offset: items.length, include_archived: includeArchived, archived_only: archivedOnly })}`, { signal });
      total = page.total;
      if (!page.items.length && items.length < total) throw new ApiError(502, "invalid_response");
      items.push(...page.items);
    } while (items.length < total);
    return { items, total };
  },
  getAnalysisSession: (id: string, signal?: AbortSignal, includeArchived = false) =>
    request<AnalysisSession>(`/analysis-sessions/${encodeURIComponent(id)}${query({ include_archived: includeArchived })}`, { signal }),
  getAnalysisConnections: (id: string, offset: number, signal?: AbortSignal, includeArchived = false, limit = 20) =>
    request<Page<AnalysisConnection>>(`/analysis-sessions/${encodeURIComponent(id)}/connections${query({ limit, offset, include_archived: includeArchived })}`, { signal }),
  getAnalysisAlerts: (id: string, offset: number, signal?: AbortSignal, includeArchived = false) =>
    request<Page<Alert>>(`/analysis-sessions/${encodeURIComponent(id)}/alerts${query({ limit: 5, offset, include_archived: includeArchived })}`, { signal }),
  getAlertConnections: (session: string, id: number, signal?: AbortSignal, includeArchived = false) =>
    request<Connection[]>(`/analysis-sessions/${encodeURIComponent(session)}/alerts/${id}/connections${query({ include_archived: includeArchived })}`, { signal }),
  archiveDatabase: () => request<ArchiveBatch>("/archives", { method: "POST" }),
  restoreArchive: (id: string) => request<ArchiveBatch>(`/archives/${encodeURIComponent(id)}/restore`, { method: "POST" }),
  getArchives: (offset: number, signal?: AbortSignal) => request<Page<ArchiveBatch>>(`/archives${query({ limit: 10, offset })}`, { signal }),
  getAlerts: (
    params: { include_archived?: boolean; archived_only?: boolean; status?: AlertStatus; provenance?: "analysis"; limit?: number; offset?: number } = {},
    signal?: AbortSignal,
  ) => request<Page<Alert>>(`/alerts${query(params)}`, { signal }),
  getDailyAlerts: (periodStart: string, timezone: string, period: "week" | "month", signal?: AbortSignal) =>
    request<DailyAlerts>(`/alerts/daily${query({ period_start: periodStart, timezone, period })}`, { signal }),
  getAlertStats: (signal?: AbortSignal) =>
    request<AlertStats>("/alerts/stats?provenance=analysis", { signal }),
  updateAlertStatuses: (ids: number[], status: AlertStatus) =>
    request<{ updated: number }>("/alerts/status", { method: "PATCH", body: JSON.stringify({ ids, status }) }),
  updateAlertStatus: (id: number, status: AlertStatus) =>
    request<Alert>(`/alerts/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  getConnections: (
    params: { include_archived?: boolean; archived_only?: boolean; proto?: string; limit?: number; offset?: number } = {},
    signal?: AbortSignal,
  ) =>
    request<Page<Connection>>(`/logs/connections${query(params)}`, { signal }),
  async downloadAlertsExport(format: "csv" | "json") {
    const response = await responseFor(
      `/alerts/export${query({ format, provenance: "analysis" })}`,
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
