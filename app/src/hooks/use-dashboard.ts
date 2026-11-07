import { useCallback } from "react";
import { api } from "@/services/api";
import type { Severity, Provenance } from "@/services/types";
import { useResource } from "./use-resource";
export function useDashboard(severity: Severity | "", offset: number, provenance: Provenance, limit: number) {
  const load = useCallback(
    async (signal: AbortSignal) => {
      const [stats, alerts, health, overview] = await Promise.all([
        api.getAlertStats(signal),
        api.getAlerts(
          { severity: severity || undefined, limit, offset, provenance },
          signal,
        ),
        api.getHealth(signal),
        api.getOverview(signal),
      ]);
      return { stats, alerts, health, overview };
    },
    [severity, offset, provenance, limit],
  );
  return useResource(load);
}
