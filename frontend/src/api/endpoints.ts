/**
 * One function per backend endpoint. Components never call fetch directly;
 * they use the hooks in ./queries.ts, which call these.
 */

import { request, toQueryString } from "./client";
import type {
  AllJobsPage,
  AllJobsParams,
  ClearResult,
  JobFacets,
  JobListParams,
  JobPage,
  RefreshResult,
  RefreshRun,
  Source,
} from "./types";

const sourcePath = (source: string) => `/sources/${encodeURIComponent(source)}`;

export const api = {
  listSources: () => request<Source[]>("/sources"),

  getSource: (source: string) => request<Source>(sourcePath(source)),

  listJobs: (source: string, params: JobListParams = {}) =>
    request<JobPage>(`${sourcePath(source)}/jobs${toQueryString(params)}`),

  getJobFacets: (source: string) => request<JobFacets>(`${sourcePath(source)}/jobs/facets`),

  listAllJobs: (params: AllJobsParams = {}) =>
    request<AllJobsPage>(`/jobs${toQueryString(params)}`),

  refreshSource: (source: string) =>
    request<RefreshResult>(`${sourcePath(source)}/refresh`, { method: "POST" }),

  /** Starts fetching every source in the background (or returns the running run). */
  startRefreshAll: () => request<RefreshRun>("/sources/refresh", { method: "POST" }),

  /** Progress of the current or last fetch-all. */
  getRefreshRun: () => request<RefreshRun>("/sources/refresh"),

  clearAll: () => request<ClearResult>("/sources/clear", { method: "POST" }),
};