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
import { useEffect, useRef } from "react";

import { api } from "./endpoints";
import type { AllJobsParams, JobListParams } from "./types";

/** How often to check a running fetch-all's progress. */
const REFRESH_POLL_MS = 1000;

export const queryKeys = {
  sources: ["sources"] as const,
  source: (source: string) => ["sources", source] as const,
  jobs: (source: string, params: JobListParams) => ["sources", source, "jobs", params] as const,
  facets: (source: string) => ["sources", source, "facets"] as const,
  // Kept under "sources" so refreshing or clearing updates it too. "@" can't
  // appear in a source name, so this never collides with one.
  allJobs: (params: AllJobsParams) => ["sources", "@all", "jobs", params] as const,
  // Not under "sources": invalidating saved data must not re-poll the run.
  refreshRun: ["refresh-run"] as const,
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

/** Jobs across every fetched source (saved data only, so always quick). */
export function useAllJobs(params: AllJobsParams) {
  return useQuery({
    queryKey: queryKeys.allJobs(params),
    queryFn: () => api.listAllJobs(params),
    placeholderData: keepPreviousData,
  });
}

/**
 * Filter options (countries, teams, ...) with counts. Pass `enabled: false`
 * until the job list has loaded: for a never-fetched source, either request
 * starts the first fetch, and a second one at the same time would be refused
 * with refresh_in_progress.
 */
export function useJobFacets(source: string, { enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: queryKeys.facets(source),
    queryFn: () => api.getJobFacets(source),
    enabled,
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

/**
 * Progress of fetching every source. Polls while a run is going, and every
 * time another source finishes, refreshes everything shown about saved data
 * (source cards, counts, today's jobs), so new data appears as it arrives.
 */
export function useRefreshRun() {
  const queryClient = useQueryClient();
  const run = useQuery({
    queryKey: queryKeys.refreshRun,
    queryFn: api.getRefreshRun,
    refetchInterval: (query) => (query.state.data?.state === "running" ? REFRESH_POLL_MS : false),
  });

  const completed = run.data?.completed;
  const lastCompleted = useRef(completed);
  useEffect(() => {
    if (completed === undefined) return;
    if (lastCompleted.current !== undefined && completed !== lastCompleted.current) {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
    }
    lastCompleted.current = completed;
  }, [completed, queryClient]);

  return run;
}

/** Start fetching every source in the background; progress via useRefreshRun. */
export function useStartRefreshAll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.startRefreshAll,
    // Show the new run straight away, which also starts the polling.
    onSuccess: (run) => queryClient.setQueryData(queryKeys.refreshRun, run),
  });
}

/** Delete all saved jobs. Cached job lists are dropped, not just marked stale,
 *  so deleted jobs never flash back on screen. */
export function useClearAll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.clearAll,
    onSuccess: () => {
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] === "sources" && query.queryKey.length > 1 });
      return queryClient.invalidateQueries({ queryKey: queryKeys.sources });
    },
  });
}