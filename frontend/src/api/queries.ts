/**
 * React Query hooks: data fetching with caching, loading and error state.
 *
 * Keys are hierarchical (["sources", name, "jobs", params]) so invalidating
 * ["sources"] after a refresh updates every list and count at once.
 */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "./endpoints";
import type { JobListParams } from "./types";

export const queryKeys = {
  sources: ["sources"] as const,
  source: (source: string) => ["sources", source] as const,
  jobs: (source: string, params: JobListParams) => ["sources", source, "jobs", params] as const,
};

export function useSources() {
  return useQuery({ queryKey: queryKeys.sources, queryFn: api.listSources });
}

export function useSource(source: string) {
  return useQuery({ queryKey: queryKeys.source(source), queryFn: () => api.getSource(source) });
}

export function useJobs(source: string, params: JobListParams) {
  return useQuery({
    queryKey: queryKeys.jobs(source, params),
    queryFn: () => api.listJobs(source, params),
    // Keep showing the current page while the next one loads.
    placeholderData: keepPreviousData,
  });
}

/** Re-scrape a source's career site, then refresh everything shown about it. */
export function useRefreshSource(source: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.refreshSource(source),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.sources }),
  });
}

/** Re-scrape every source, then refresh everything shown. */
export function useRefreshAll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.refreshAll,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.sources }),
  });
}

/** Delete all saved jobs. Cached job lists are dropped, not just marked stale,
 *  so deleted jobs never flash back on screen. */
export function useClearAll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.clearAll,
    onSuccess: () => {
      queryClient.removeQueries({ predicate: (query) => query.queryKey.length > 1 });
      return queryClient.invalidateQueries({ queryKey: queryKeys.sources });
    },
  });
}