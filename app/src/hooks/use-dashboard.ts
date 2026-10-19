import { useCallback } from "react";
import { api } from "@/services/api";
import type { Severity } from "@/services/types";
import { TIMING } from "@/constants";
import { useResource } from "./use-resource";
export const ALERT_PAGE_SIZE = 25;
export function useDashboard(severity: Severity | "", offset: number) {
  const load = useCallback(
    async (signal: AbortSignal) => {
      const [stats, alerts, health] = await Promise.all([
        api.getAlertStats(signal),
        api.getAlerts(
          { severity: severity || undefined, limit: ALERT_PAGE_SIZE, offset },
          signal,
        ),
        api.getHealth(signal),
      ]);
      return { stats, alerts, health };
    },
    [severity, offset],
  );
  return useResource(load, TIMING.DASHBOARD_POLL_INTERVAL);
}
