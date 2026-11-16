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

import { bumpLogoVersion } from "../utils/logoVersion";
import { api } from "./endpoints";
import type {
  AllJobsParams,
  CatalogEntryInput,
  CheckInput,
  JobListParams,
  MonitorSettings,
} from "./types";

/** How often to check a running fetch-all's progress. */
const REFRESH_POLL_MS = 1000;
/** After the monitor starts, wait this long for its first fetch to begin. */
const MONITOR_START_DELAY_MS = 1000;

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
  catalog: ["catalog"] as const,
  catalogEntry: (name: string) => ["catalog", name] as const,
  // Kept up to date every 15 seconds by AlertListener.
  monitor: ["monitor"] as const,
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
 * Progress of fetching every source. Polls every second while a run is
 * going, and every time another source finishes, refreshes everything shown
 * about saved data (source cards, counts, today's jobs), so new data appears
 * as it arrives.
 *
 * Runs started by the monitor happen in the background, so this also
 * watches the monitor's status: when the monitor starts (a new started_at)
 * or reports it's fetching, the run is reloaded, which starts the polling.
 */
export function useRefreshRun() {
  const queryClient = useQueryClient();
  const run = useQuery({
    queryKey: queryKeys.refreshRun,
    queryFn: api.getRefreshRun,
    refetchInterval: (query) => (query.state.data?.state === "running" ? REFRESH_POLL_MS : false),
  });
  const monitor = useMonitor().data;

  // Each finished source: refresh the saved data shown.
  const completed = run.data?.completed;
  const lastCompleted = useRef(completed);
  useEffect(() => {
    if (completed === undefined) return;
    if (lastCompleted.current !== undefined && completed !== lastCompleted.current) {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources });
    }
    lastCompleted.current = completed;
  }, [completed, queryClient]);

  // The monitor just started: its first fetch begins a moment later.
  const monitorStartedAt = monitor?.active ? monitor.started_at : null;
  useEffect(() => {
    if (!monitorStartedAt) return;
    const timer = window.setTimeout(
      () => queryClient.invalidateQueries({ queryKey: queryKeys.refreshRun }),
      MONITOR_START_DELAY_MS,
    );
    return () => window.clearTimeout(timer);
  }, [monitorStartedAt, queryClient]);

  // The monitor reports a fetch this page hasn't seen yet.
  const monitorFetching = monitor?.fetching ?? false;
  const runRunning = run.data?.state === "running";
  useEffect(() => {
    if (monitorFetching && !runRunning) {
      void queryClient.invalidateQueries({ queryKey: queryKeys.refreshRun });
    }
  }, [monitorFetching, runRunning, queryClient]);

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

// Managing sources -----------------------------------------------------------

/** The platforms, and whether editing sources is allowed. */
export function useCatalog() {
  return useQuery({ queryKey: queryKeys.catalog, queryFn: api.getCatalog });
}

/** One source's catalog entry, for the edit form. */
export function useCatalogEntry(name: string, { enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: queryKeys.catalogEntry(name),
    queryFn: () => api.getCatalogEntry(name),
    enabled,
  });
}

/** Check board names before saving (one request per board, like a refresh). */
export function useCheckBoards() {
  return useMutation({ mutationFn: (input: CheckInput) => api.checkBoards(input) });
}

interface SaveSourceArgs {
  /** The source being edited; absent when adding. */
  editing?: string;
  input: CatalogEntryInput;
  /** A new PNG logo to upload after saving. */
  logo?: File | null;
  /** Remove the current logo (ignored when a new one is given). */
  removeLogo?: boolean;
}

/** Add or edit a source, then upload or remove its logo. */
export function useSaveSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ editing, input, logo, removeLogo }: SaveSourceArgs) => {
      const entry = editing ? await api.updateSource(editing, input) : await api.addSource(input);
      if (logo) {
        await api.uploadLogo(entry.name, logo);
        bumpLogoVersion();
      } else if (removeLogo) {
        await api.deleteLogo(entry.name);
        bumpLogoVersion();
      }
      return entry;
    },
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.sources }),
        queryClient.invalidateQueries({ queryKey: queryKeys.catalog }),
      ]),
  });
}

/** Delete a source: its catalog entry, saved jobs and logo. */
export function useDeleteSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.deleteSource(name),
    onSuccess: (_result, name) => {
      bumpLogoVersion();
      queryClient.removeQueries({ queryKey: queryKeys.source(name) });
      queryClient.removeQueries({ queryKey: queryKeys.catalogEntry(name) });
      return Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.sources }),
        queryClient.invalidateQueries({ queryKey: queryKeys.catalog }),
      ]);
    },
  });
}

// Monitor --------------------------------------------------------------------

/** The monitor's settings and status (also refreshed by AlertListener). */
export function useMonitor() {
  return useQuery({ queryKey: queryKeys.monitor, queryFn: api.getMonitor });
}

/** A monitor action whose response is the new status, stored straight away. */
function useMonitorMutation<TArgs>(action: (args: TArgs) => ReturnType<typeof api.getMonitor>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: (status) => queryClient.setQueryData(queryKeys.monitor, status),
  });
}

export function useSaveMonitorSettings() {
  return useMonitorMutation((settings: MonitorSettings) => api.saveMonitorSettings(settings));
}

/** Save the settings, then start monitoring. */
export function useStartMonitor() {
  return useMonitorMutation(async (settings: MonitorSettings) => {
    await api.saveMonitorSettings(settings);
    return api.startMonitor();
  });
}

export function useStopMonitor() {
  return useMonitorMutation((_: void) => api.stopMonitor());
}

/** Play the chime on this computer, as an alert would. */
export function useTestSound() {
  return useMutation({ mutationFn: api.testSound });
}

export function useSendTestEmail() {
  return useMutation({ mutationFn: (emailTo: string) => api.sendTestEmail(emailTo) });
}

export function useConfirmEmail() {
  return useMonitorMutation(({ emailTo, received }: { emailTo: string; received: boolean }) =>
    api.confirmEmail(emailTo, received),
  );
}