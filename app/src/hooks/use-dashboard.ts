import { useCallback, useMemo } from "react";
import { api } from "@/services/api";
import type { Severity, Provenance } from "@/services/types";
import { useResource } from "./use-resource";

export function useDashboard(
  severity: Severity | "",
  offset: number,
  provenance: Provenance,
  limit: number,
) {
  // Base dashboard data (stats, health, overview) is fetched independently of alerts pagination.
  const loadOverview = useCallback(
    async (signal: AbortSignal) => {
      const [stats, health, overview] = await Promise.all([
        api.getAlertStats(signal),
        api.getHealth(signal),
        api.getOverview(signal),
      ]);
      return { stats, health, overview };
    },
    [],
  );
  const overviewResource = useResource(loadOverview, true, 0, "dashboard:overview");

  // Paginated alerts: only requests alerts when changing page or filters.
  const loadAlerts = useCallback(
    (signal: AbortSignal) =>
      api.getAlerts(
        { severity: severity || undefined, limit, offset, provenance },
        signal,
      ),
    [severity, limit, offset, provenance],
  );
  const alertsCacheKey = `dashboard:alerts:${severity}:${provenance}:${limit}:${offset}`;
  const alertsResource = useResource(loadAlerts, true, 0, alertsCacheKey);

  const data = useMemo(() => {
    if (!overviewResource.data || !alertsResource.data) return null;
    return {
      stats: overviewResource.data.stats,
      health: overviewResource.data.health,
      overview: overviewResource.data.overview,
      alerts: alertsResource.data,
    };
  }, [overviewResource.data, alertsResource.data]);

  const refresh = useCallback(async () => {
    await Promise.all([
      overviewResource.refresh(),
      alertsResource.refresh(),
    ]);
  }, [overviewResource, alertsResource]);

  return {
    data,
    loading: overviewResource.loading || alertsResource.loading,
    alertsLoading: alertsResource.loading,
    error: overviewResource.error || alertsResource.error,
    refresh,
  };
}
