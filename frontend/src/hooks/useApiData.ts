"use client";

import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Generic hook for fetching API data with loading/error states.
 * Re-fetches when `deps` change. Pass null fetcher to skip.
 */
export function useApiData<T>(
  fetcher: (() => Promise<T>) | null,
  deps: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(!!fetcher);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const reload = useCallback(async () => {
    const currentFetcher = fetcherRef.current;
    if (!currentFetcher) return;
    setLoading(true);
    setError(null);
    try {
      const result = await currentFetcher();
      setData(result);
    } catch (e: any) {
      setError(e.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload, setData };
}
