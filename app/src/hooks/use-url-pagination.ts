import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { DEFAULT_PAGE_SIZE } from "@/constants";

export interface UseUrlPaginationOptions {
  pageParam?: string;
  limitParam?: string;
  defaultLimit?: number;
}

export function useUrlPagination({
  pageParam = "page",
  limitParam = "limit",
  defaultLimit = DEFAULT_PAGE_SIZE,
}: UseUrlPaginationOptions = {}) {
  const [searchParams, setSearchParams] = useSearchParams();

  const page = useMemo(() => {
    const raw = searchParams.get(pageParam);
    if (!raw) return 1;
    const num = parseInt(raw, 10);
    return isNaN(num) || num < 1 ? 1 : num;
  }, [searchParams, pageParam]);

  const limit = useMemo(() => {
    if (!limitParam) return defaultLimit;
    const raw = searchParams.get(limitParam);
    if (!raw) return defaultLimit;
    const num = parseInt(raw, 10);
    return isNaN(num) || num < 1 ? defaultLimit : num;
  }, [searchParams, limitParam, defaultLimit]);

  const offset = (page - 1) * limit;

  const setPage = useCallback(
    (newPage: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (newPage <= 1) {
          next.delete(pageParam);
        } else {
          next.set(pageParam, String(newPage));
        }
        return next;
      });
    },
    [setSearchParams, pageParam],
  );

  const setOffset = useCallback(
    (newOffset: number) => {
      const targetPage = Math.floor(newOffset / limit) + 1;
      setPage(targetPage);
    },
    [limit, setPage],
  );

  const setLimit = useCallback(
    (newLimit: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (limitParam) {
          if (newLimit === defaultLimit) {
            next.delete(limitParam);
          } else {
            next.set(limitParam, String(newLimit));
          }
        }
        next.delete(pageParam);
        return next;
      });
    },
    [setSearchParams, limitParam, defaultLimit, pageParam],
  );

  const resetPage = useCallback(() => {
    setSearchParams((prev) => {
      if (!prev.has(pageParam)) return prev;
      const next = new URLSearchParams(prev);
      next.delete(pageParam);
      return next;
    });
  }, [setSearchParams, pageParam]);

  return {
    page,
    limit,
    offset,
    setPage,
    setOffset,
    setLimit,
    resetPage,
  };
}
