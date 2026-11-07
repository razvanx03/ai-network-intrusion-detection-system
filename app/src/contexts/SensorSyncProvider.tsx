import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { api, ApiError } from "@/services/api";
import type { AnalysisResult } from "@/services/types";
import { clearResourceCache } from "@/hooks/use-resource";
import { SensorSyncContext } from "./sensor-sync-context";

export function SensorSyncProvider({ children }: { children: ReactNode }) {
  const [syncing, setSyncing] = useState(false);
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const pending = useRef<Promise<AnalysisResult> | null>(null);
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const analyze = useCallback((automatic = false): Promise<AnalysisResult> => {
    if (pending.current) return pending.current;
    setSyncing(true);
    setError(null);
    const task = api.fetchAndAnalyze().catch((failure: unknown) => {
      if (active.current && automatic && !(failure instanceof ApiError && [401, 403, 409].includes(failure.status))) setError(failure);
      throw failure;
    }).finally(() => {
      pending.current = null;
      if (active.current) {
        setSyncing(false);
        // Also refresh committed batches after a partially failed run.
        clearResourceCache();
        setRevision(value => value + 1);
      }
    });
    pending.current = task;
    return task;
  }, []);
  return <SensorSyncContext.Provider value={{ syncing, revision, error, dismissError: () => setError(null), analyze }}>{children}</SensorSyncContext.Provider>;
}
