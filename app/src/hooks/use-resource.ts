import { useCallback, useEffect, useRef, useState } from "react";
// One request per resource; replacement requests abort and invalidate old results.
export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  interval?: number,
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const pending = useRef<AbortController | null>(null);
  const active = useRef(false);
  const refresh = useCallback(async () => {
    if (!active.current) return;
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
    // A new server query invalidates the previous query result.
    // oxlint-disable-next-line react/set-state-in-effect
    setData(null);
    void refresh();
    const timer = interval
      ? setInterval(() => {
          if (!pending.current) void refresh();
        }, interval)
      : undefined;
    return () => {
      active.current = false;
      if (timer) clearInterval(timer);
      pending.current?.abort();
      pending.current = null;
    };
  }, [refresh, interval]);
  return { data, error, loading, refresh };
}
