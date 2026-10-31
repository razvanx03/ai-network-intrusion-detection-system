import { useCallback } from "react";
import { api } from "@/services/api";
import type { Severity, Provenance } from "@/services/types";
import { TIMING } from "@/constants";
import { useResource } from "./use-resource";
export const ALERT_PAGE_SIZE = 25;
export function useDashboard(severity: Severity | "", offset: number, provenance: Provenance) {
  const load = useCallback(
    async (signal: AbortSignal) => {
      const [stats, alerts, health, overview] = await Promise.all([
        api.getAlertStats(signal),
        api.getAlerts(
          { severity: severity || undefined, limit: ALERT_PAGE_SIZE, offset, provenance },
          signal,
        ),
        api.getHealth(signal),
        api.getOverview(signal),
      ]);
      return { stats, alerts, health, overview };
    },
    [severity, offset, provenance],
  );
  return useResource(load, TIMING.DASHBOARD_POLL_INTERVAL);
}
