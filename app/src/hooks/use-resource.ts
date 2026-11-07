import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { SensorSyncContext } from "@/contexts/sensor-sync-context";

interface CacheEntry<T> {
  data: T;
  revision: number;
  refreshVersion: number;
}

// Module-level cache for paginated resource pages.
// Automatically invalidated whenever sensor sync revision increments (e.g. the 1-minute background ingestion)
// or when a caller's refreshVersion changes (e.g. database archive/restore).
const resourceCache = new Map<string, CacheEntry<unknown>>();

export function clearResourceCache() {
  resourceCache.clear();
}

// One request per resource; replacement requests abort and invalidate old results.
export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  loadOnMount = true,
  refreshVersion = 0,
  cacheKey?: string,
) {
  const revision = useContext(SensorSyncContext)?.revision ?? 0;
  const previousRevision = useRef(revision);
  const previousRefreshVersion = useRef(refreshVersion);

  const getCachedData = useCallback((): T | null => {
    if (!cacheKey) return null;
    const entry = resourceCache.get(cacheKey) as CacheEntry<T> | undefined;
    if (entry && entry.revision === revision && entry.refreshVersion === refreshVersion) {
      return entry.data;
    }
    return null;
  }, [cacheKey, revision, refreshVersion]);

  // Adjust state during render if cacheKey changed and we have cached data
  const [currentKey, setCurrentKey] = useState(cacheKey);
  const [data, setData] = useState<T | null>(() => getCachedData());
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(() => loadOnMount && getCachedData() === null);

  if (cacheKey !== currentKey) {
    setCurrentKey(cacheKey);
    const cached = getCachedData();
    if (cached !== null) {
      setData(cached);
      setLoading(false);
      setError(null);
    }
  }

  const requested = useRef(loadOnMount);
  const pending = useRef<AbortController | null>(null);
  const active = useRef(false);
  const hasData = useRef(data !== null);

  const refresh = useCallback(
    async (background = false, force = false) => {
      if (!active.current) return;
      requested.current = true;

      // When force is explicitly requested (e.g. user retrying or manual action), evict cache
      if (force && cacheKey) {
        resourceCache.delete(cacheKey);
      }

      // If not forcing and data is in cache, serve immediately without DB/network request
      if (!force && cacheKey) {
        const cached = getCachedData();
        if (cached !== null) {
          pending.current?.abort();
          pending.current = null;
          hasData.current = true;
          setData(cached);
          setLoading(false);
          setError(null);
          return;
        }
      }

      pending.current?.abort();
      const controller = new AbortController();
      pending.current = controller;
      if (!background || !hasData.current) setLoading(true);
      setError(null);
      try {
        const value = await load(controller.signal);
        if (!controller.signal.aborted) {
          hasData.current = true;
          if (cacheKey) {
            if (resourceCache.size > 200) {
              const oldestKey = resourceCache.keys().next().value;
              if (oldestKey) resourceCache.delete(oldestKey);
            }
            resourceCache.set(cacheKey, {
              data: value,
              revision,
              refreshVersion,
            });
          }
          setData(value);
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(err);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          pending.current = null;
        }
      }
    },
    [load, cacheKey, getCachedData, revision, refreshVersion],
  );

  useEffect(() => {
    active.current = true;
    const revisionChanged = previousRevision.current !== revision;
    const refreshVersionChanged = previousRefreshVersion.current !== refreshVersion;

    previousRevision.current = revision;
    previousRefreshVersion.current = refreshVersion;

    if (revisionChanged) {
      clearResourceCache();
    } else if (refreshVersionChanged && cacheKey) {
      resourceCache.delete(cacheKey);
    }

    // If cacheKey has cached data, no fetch is needed!
    const cached = getCachedData();
    if (cached !== null && !revisionChanged && !refreshVersionChanged) {
      return;
    }

    const background = revisionChanged;
    if (requested.current || revisionChanged || refreshVersionChanged) {
      void refresh(background, revisionChanged || refreshVersionChanged);
    }

    return () => {
      active.current = false;
      pending.current?.abort();
      pending.current = null;
    };
  }, [refresh, refreshVersion, revision, cacheKey, getCachedData]);

  return {
    data,
    error,
    loading,
    refresh: (background = false) => refresh(background, true),
  };
}
