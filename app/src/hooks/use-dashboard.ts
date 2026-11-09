import { useCallback, useMemo } from "react";
import { api } from "@/services/api";
import { useResource } from "./use-resource";

export function useDashboard(
  offset: number,
  limit: number,
) {
  // Base dashboard data (stats, overview) is fetched independently of alerts pagination.
  const loadOverview = useCallback(
    async (signal: AbortSignal) => {
      const [stats, overview] = await Promise.all([
        api.getAlertStats(signal),
        api.getOverview(signal),
      ]);
      return { stats, overview };
    },
    [],
  );
  const overviewResource = useResource(loadOverview, true, 0, "dashboard:overview");

  // Paginated alerts: only requests alerts when changing page or filters.
  const loadAlerts = useCallback(
    (signal: AbortSignal) =>
      api.getAlerts(
        { limit, offset, provenance: "analysis" },
        signal,
      ),
    [limit, offset],
  );
  const alertsCacheKey = `dashboard:alerts:analysis:${limit}:${offset}`;
  const alertsResource = useResource(loadAlerts, true, 0, alertsCacheKey);

  const data = useMemo(() => {
    if (!overviewResource.data || !alertsResource.data) return null;
    return {
      stats: overviewResource.data.stats,
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
