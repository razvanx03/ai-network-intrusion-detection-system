import { useCallback, useEffect, useRef, useState } from "react";
// One request per resource; replacement requests abort and invalidate old results.
export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  loadOnMount = true,
  refreshVersion = 0,
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(loadOnMount);
  const requested = useRef(loadOnMount);
  const pending = useRef<AbortController | null>(null);
  const active = useRef(false);
  const refresh = useCallback(async () => {
    if (!active.current) return;
    requested.current = true;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    setError(null);
    try {
      const value = await load(controller.signal);
      if (!controller.signal.aborted) setData(value);
    } catch (err) {
      if (!controller.signal.aborted) setError(err);
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
        pending.current = null;
      }
    }
  }, [load]);
  useEffect(() => {
    active.current = true;
    // Retain the last result so refreshes never unmount the surrounding UI.
    // Query changes follow explicit filter/pagination clicks. No timers.
    if (requested.current) void refresh();
    return () => {
      active.current = false;
      pending.current?.abort();
      pending.current = null;
    };
  }, [refresh, refreshVersion]);
  return { data, error, loading, refresh };
}
