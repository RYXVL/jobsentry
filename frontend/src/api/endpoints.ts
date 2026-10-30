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
  RefreshAllResult,
  RefreshResult,
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

  refreshAll: () => request<RefreshAllResult>("/sources/refresh", { method: "POST" }),

  clearAll: () => request<ClearResult>("/sources/clear", { method: "POST" }),
};